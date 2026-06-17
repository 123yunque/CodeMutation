import ast
import json
import os
import random
import re


DATASET_NAME = "evalplus/mbppplus"
DATASET_SPLIT = "test"

COMBINED_HEADER = """
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
inputs_file = os.path.join(current_dir, 'code_inputs.txt')
results_file = os.path.join(current_dir, 'code_results.txt')
"""


def process_test_field(test_str):
    def remove_assertion_tail(line):
        if "assertion" in line:
            return line.split(")")[0] + ")"
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
    match = re.search(r"inputs\s*=\s*(\[.*?\])\s*\nresults", test_processed, re.DOTALL)
    if match:
        return parse_inputs_literal(match.group(1))

    inputs_literal = extract_inputs_assignment_literal(test_processed)
    if not inputs_literal:
        return []
    return parse_inputs_literal(inputs_literal)


def extract_inputs_assignment_literal(test_processed):
    match = re.search(r"\binputs\s*=", test_processed)
    if not match:
        return None

    start = test_processed.find("[", match.end())
    if start == -1:
        return None

    stack = []
    quote = None
    escape = False
    for index in range(start, len(test_processed)):
        char = test_processed[index]

        if quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            continue

        if char in {"'", '"'}:
            quote = char
        elif char in "[({":
            stack.append(char)
        elif char in "])}":
            if not stack:
                return None
            opening = stack.pop()
            if (opening, char) not in {("[", "]"), ("(", ")"), ("{", "}")}:
                return None
            if not stack:
                return test_processed[start : index + 1]

    return None


def build_combined_lines(test_processed, model_footer):
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
            combined_lines.append("    result.append(" + line[14:] + ")")
        else:
            combined_lines.append(line)

    if model_footer:
        combined_lines.append(model_footer)
    return combined_lines, results_lines


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
    task_id = int(item["task_id"])
    folder_path = os.path.join(output_dir, f"task_{task_id}")
    if os.path.exists(folder_path) and not overwrite:
        return "skipped"
    os.makedirs(folder_path, exist_ok=True)

    json_path = os.path.join(folder_path, f"task_{task_id}.json")
    combined_path = os.path.join(folder_path, "combined.py")
    results_path = os.path.join(folder_path, "results.txt")
    code_path = os.path.join(folder_path, "code.py")
    inputs_path = os.path.join(folder_path, "code_inputs.txt")
    sample_inputs_path = os.path.join(folder_path, "sample_code_inputs.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=4)

    if isinstance(item.get("test"), str):
        test_processed = process_test_field(item["test"])
    elif isinstance(item.get("test"), list):
        test_processed = "\n".join(process_test_field(test) for test in item["test"])
    else:
        test_processed = ""

    inputs_list = extract_inputs(test_processed)
    if inputs_list:
        write_lines(inputs_path, inputs_list)
        sampled_inputs = random.sample(inputs_list, min(sample_size, len(inputs_list)))
        write_lines(sample_inputs_path, sampled_inputs)

    combined_lines, results_lines = build_combined_lines(test_processed, model_footer)
    code_content = item.get("code", "")

    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(code_content + "\n")
        f.write("\n".join(combined_lines) + "\n")

    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code_content + "\n")

    if results_lines:
        with open(results_path, "w", encoding="utf-8") as f:
            f.write("\n".join(results_lines))

    return "written"


def load_mbppplus():
    from datasets import load_dataset

    return load_dataset(DATASET_NAME)[DATASET_SPLIT]


def generate_dataset(output_dir, model_footer, sample_size=10, seed=0, overwrite=False, limit=None):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    dataset = load_mbppplus()

    stats = {"written": 0, "skipped": 0, "failed": 0}
    total = len(dataset) if limit is None else min(limit, len(dataset))
    print(f"Loading {total} tasks into {output_dir}")

    for index, item in enumerate(dataset):
        if limit is not None and index >= limit:
            break
        try:
            status = save_item(item, output_dir, model_footer, sample_size, overwrite)
        except Exception as exc:
            stats["failed"] += 1
            print(f"[failed] task_{item.get('task_id')}: {exc}")
            continue

        if status == "written":
            stats["written"] += 1
            print(f"[written] task_{item['task_id']}")
        else:
            stats["skipped"] += 1
            print(f"[skip] task_{item['task_id']} exists")

    return stats
