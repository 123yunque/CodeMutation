import ast
import json
import os
import random
import re


DEFAULT_DATASET_KEY = "humanevalplus"
DATASET_CONFIGS = {
    "mbppplus": {
        "hf_name": "evalplus/mbppplus",
        "split": "test",
        "execution_type": "function_call",
    },
    "humanevalplus": {
        "hf_name": "evalplus/humanevalplus",
        "split": "test",
        "execution_type": "function_call",
    },
    "codecontestplus": {
        "hf_name": "ByteDance-Seed/CodeContestsPlus",
        "split": "test",
        "execution_type": "stdio",
    },
}
DATASET_SPLIT = "test"

COMBINED_HEADER = """
import os
import sys

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

current_dir = os.path.dirname(os.path.abspath(__file__))
inputs_file = os.path.join(current_dir, 'code_inputs.txt')
results_file = os.path.join(current_dir, 'code_results.txt')
"""


def process_test_field(test_str):
    def remove_assertion_tail(line):
        return line

    keyword = "inputs"
    idx = test_str.find(keyword)
    lines = test_str[idx:].splitlines() if idx != -1 else test_str.splitlines()
    return "\n".join(remove_assertion_tail(line) for line in lines)


def parse_inputs_literal(inputs_str):
    tree = ast.parse(inputs_str, mode="eval")
    allowed_nodes = (
        ast.Expression,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Set,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.UnaryOp,
        ast.UAdd,
        ast.USub,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"Unsupported input literal node: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in {"inf", "nan"}:
            raise ValueError(f"Unsupported name in input literal: {node.id}")

    return eval(compile(tree, "<inputs>", "eval"), {"__builtins__": {}}, {"inf": float("inf"), "nan": float("nan")})


def extract_inputs(test_processed):
    match = re.search(r"inputs\s*=\s*(\[.*?\])\s*\n\s*results", test_processed, re.DOTALL)
    if match:
        return parse_inputs_literal(match.group(1))

    match = re.search(r"inputs\s*=\s*(\[.*?\])\s*(?=\n\s*(?:for|assertion|assert|$))", test_processed, re.DOTALL)
    if match:
        return parse_inputs_literal(match.group(1))

    try:
        tree = ast.parse(test_processed)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "inputs":
                return parse_inputs_literal(ast.unparse(node.value))
    return []


def extract_assertion_output_expression(line, entry_point=None):
    stripped = line.strip()
    try:
        tree = ast.parse(stripped, mode="exec")
        call = tree.body[0].value
        if isinstance(call, ast.Call) and call.args:
            expression = ast.unparse(call.args[0])
        else:
            expression = stripped[len("assertion(") :].rsplit(")", 1)[0]
    except (SyntaxError, AttributeError, IndexError):
        expression = stripped[len("assertion(") :].rsplit(")", 1)[0]

    if entry_point and "candidate(" in expression:
        expression = expression.replace("candidate(", f"{entry_point}(")
    return expression


def safe_task_id(task_id):
    return re.sub(r"[^0-9A-Za-z_]+", "_", str(task_id)).strip("_")


def get_first_function_name(code_content, default=None):
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return default

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return default


def normalize_input_case(input_case):
    if isinstance(input_case, tuple):
        return list(input_case)
    return input_case


def normalize_mbppplus_item(item):
    code_content = item.get("code", "")
    return {
        **dict(item),
        "dataset": "mbppplus",
        "raw_task_id": item.get("task_id"),
        "task_id": safe_task_id(item.get("task_id")),
        "safe_task_id": safe_task_id(item.get("task_id")),
        "code": code_content,
        "entry_point": item.get("entry_point") or get_first_function_name(code_content),
        "execution_type": "function_call",
        "inputs": None,
        "raw": dict(item),
    }


def normalize_humanevalplus_item(item):
    raw_task_id = item.get("task_id")
    code_content = (item.get("prompt") or "") + (item.get("canonical_solution") or "")
    test_processed = process_test_field(item.get("test", "")) if item.get("test") else ""
    inputs = list(item.get("base_input") or []) + list(item.get("plus_input") or [])
    if not inputs and test_processed:
        inputs = extract_inputs(test_processed)
    inputs = [normalize_input_case(input_case) for input_case in inputs]
    safe_id = safe_task_id(raw_task_id)
    return {
        "dataset": "humanevalplus",
        "raw_task_id": raw_task_id,
        "task_id": safe_id,
        "safe_task_id": safe_id,
        "prompt": item.get("prompt", ""),
        "test": item.get("test", ""),
        "code": code_content,
        "entry_point": item.get("entry_point") or get_first_function_name(code_content),
        "execution_type": "function_call",
        "inputs": inputs,
        "raw": dict(item),
    }


def normalize_codecontestplus_item(item):
    raise NotImplementedError(
        "CodeContestsPlus is a stdio contest dataset. Its adapter must map a selected "
        "submission and generated tests into {'stdin': ..., 'expected': ...} cases "
        "before it can use this project's current function-call RQ pipeline."
    )


def normalize_item(item, dataset_key):
    if dataset_key == "mbppplus":
        return normalize_mbppplus_item(item)
    if dataset_key == "humanevalplus":
        return normalize_humanevalplus_item(item)
    if dataset_key == "codecontestplus":
        return normalize_codecontestplus_item(item)
    raise ValueError(f"Unsupported dataset: {dataset_key}")


def build_combined_lines(test_processed, model_footer, entry_point=None):
    combined_lines = [COMBINED_HEADER]
    results_lines = []
    cycle_head = "result = []\nfor inp in inputs:"

    for line in test_processed.splitlines():
        stripped = line.strip()
        if stripped.startswith("results"):
            results_lines.append(line[10:])
        elif stripped.startswith("for"):
            combined_lines.append(cycle_head)
        elif stripped.startswith("assertion"):
            combined_lines.append("    result.append(" + extract_assertion_output_expression(line, entry_point) + ")")
        else:
            combined_lines.append(line)

    if model_footer:
        combined_lines.append(model_footer)
    return combined_lines, results_lines


def build_function_combined_lines(inputs_list, entry_point, model_footer):
    combined_lines = [
        COMBINED_HEADER,
        "inputs = [",
        *[f"    {repr(input_case)}," for input_case in inputs_list],
        "]",
        "result = []",
        "for inp in inputs:",
        f"    result.append({entry_point}(*inp))",
        "",
        "with open(results_file, 'w', encoding='utf-8') as f:",
        "    for item in result:",
        "        f.write(str(item) + '\\n')",
    ]
    if model_footer:
        combined_lines.append(model_footer)
    return combined_lines


def read_model_footer(model_path):
    if not os.path.exists(model_path):
        return ""
    with open(model_path, "r", encoding="utf-8") as f:
        return f.read()


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(repr(line) + "\n")


def save_item(item, output_dir, model_footer, sample_size, overwrite):
    task_id = item["safe_task_id"]
    folder_path = os.path.join(output_dir, f"task_{task_id}")
    if os.path.exists(folder_path) and not overwrite:
        required_files = (
            f"task_{task_id}.json",
            "meta.json",
            "combined.py",
            "code.py",
            "code_inputs.txt",
            "sample_code_inputs.txt",
        )
        if all(os.path.exists(os.path.join(folder_path, name)) for name in required_files):
            return "skipped"
    os.makedirs(folder_path, exist_ok=True)

    json_path = os.path.join(folder_path, f"task_{task_id}.json")
    meta_path = os.path.join(folder_path, "meta.json")
    combined_path = os.path.join(folder_path, "combined.py")
    results_path = os.path.join(folder_path, "results.txt")
    code_path = os.path.join(folder_path, "code.py")
    inputs_path = os.path.join(folder_path, "code_inputs.txt")
    sample_inputs_path = os.path.join(folder_path, "sample_code_inputs.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=4)

    meta = {
        "dataset": item.get("dataset"),
        "task_id": item.get("raw_task_id", item.get("task_id")),
        "safe_task_id": item.get("safe_task_id"),
        "entry_point": item.get("entry_point"),
        "execution_type": item.get("execution_type", "function_call"),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=4)

    if isinstance(item.get("test"), str):
        test_processed = process_test_field(item["test"])
    elif isinstance(item.get("test"), list):
        test_processed = "\n".join(process_test_field(test) for test in item["test"])
    else:
        test_processed = ""

    inputs_list = item.get("inputs") or extract_inputs(test_processed)
    if not inputs_list:
        raise ValueError("No input cases found")
    if inputs_list:
        write_lines(inputs_path, inputs_list)
        sampled_inputs = random.sample(inputs_list, min(sample_size, len(inputs_list)))
        write_lines(sample_inputs_path, sampled_inputs)

    code_content = item.get("code", "")
    if test_processed:
        combined_lines, results_lines = build_combined_lines(test_processed, model_footer, item.get("entry_point"))
    else:
        combined_lines = build_function_combined_lines(inputs_list, item.get("entry_point"), model_footer)
        results_lines = []

    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(code_content + "\n")
        f.write("\n".join(combined_lines) + "\n")

    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code_content + "\n")

    if results_lines:
        with open(results_path, "w", encoding="utf-8") as f:
            f.write("\n".join(results_lines))

    return "written"


def load_hf_dataset(dataset_key):
    from datasets import load_dataset

    config = DATASET_CONFIGS[dataset_key]
    return load_dataset(config["hf_name"])[config.get("split", DATASET_SPLIT)]


def load_humanevalplus_from_evalplus():
    from evalplus.data import get_human_eval_plus  # type: ignore[import-untyped]

    dataset = get_human_eval_plus()
    if isinstance(dataset, dict):
        return list(dataset.values())
    return dataset


def load_dataset_items(dataset_key):
    if dataset_key == "humanevalplus":
        try:
            return load_humanevalplus_from_evalplus()
        except Exception as exc:
            print(f"[warn] evalplus loader failed, falling back to HuggingFace datasets: {exc}")
    return load_hf_dataset(dataset_key)


def generate_dataset(
    output_dir,
    model_footer,
    sample_size=10,
    seed=0,
    overwrite=False,
    limit=None,
    dataset_key=DEFAULT_DATASET_KEY,
):
    if dataset_key not in DATASET_CONFIGS:
        raise ValueError(f"Unsupported dataset: {dataset_key}. Valid datasets: {', '.join(DATASET_CONFIGS)}")

    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    dataset = load_dataset_items(dataset_key)

    stats = {"written": 0, "skipped": 0, "failed": 0}
    total = len(dataset) if limit is None else min(limit, len(dataset))
    print(f"Loading {total} {dataset_key} tasks into {output_dir}")

    for index, item in enumerate(dataset):
        if limit is not None and index >= limit:
            break
        try:
            normalized_item = normalize_item(item, dataset_key)
            status = save_item(normalized_item, output_dir, model_footer, sample_size, overwrite)
        except Exception as exc:
            stats["failed"] += 1
            print(f"[failed] task_{item.get('task_id')}: {exc}")
            continue

        if status == "written":
            stats["written"] += 1
            print(f"[written] task_{normalized_item['safe_task_id']}")
        else:
            stats["skipped"] += 1
            print(f"[skip] task_{normalized_item['safe_task_id']} exists")

    return stats
