import ast
import json
import os

from paths import EQUIV_TRANSFORM, MBPP_DIR, NON_EQUIV_TRANSFORM


ORIGINAL_OUTPUT_TEMPLATE = """
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
inputs_file = os.path.join(current_dir, 'sample_code_inputs.txt')
results_file = os.path.join(current_dir, 'sample_code_results.txt')
result = []
for inp in inputs:
    result.append({func_name}(*inp))
"""

MUTATION_OUTPUT_TEMPLATE = """
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
results_file = os.path.join(current_dir, '{result_file}')

result = []
for inp in inputs:
    result.append({func_name}(*inp))

with open(results_file, 'w', encoding='utf-8') as f:
    for item in result:
        f.write(str(item) + "\\n")
"""


def read_model_footer():
    model_path = os.path.join(os.path.dirname(__file__), "model.py")
    if not os.path.exists(model_path):
        print(f"[warn] missing model footer: {model_path}")
        return ""
    with open(model_path, "r", encoding="utf-8") as f:
        return f.read()


def read_input_literals(path):
    if not os.path.exists(path):
        return []
    inputs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                inputs.append(line)
    return inputs


def parse_input_lines(path):
    parsed_inputs = []
    if not os.path.exists(path):
        return parsed_inputs

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parsed_inputs.append(ast.literal_eval(line))
            except (SyntaxError, ValueError):
                parsed_inputs.append(line)
    return parsed_inputs


def get_first_function_name(code_content, default=None):
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return default

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return default


def get_entry_point(task_dir, code_content, default=None):
    meta_path = os.path.join(task_dir, "meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("entry_point"):
                return meta["entry_point"]
        except (OSError, json.JSONDecodeError):
            pass
    return get_first_function_name(code_content, default=default)


def build_inputs_block(items, use_repr=False):
    lines = ["\n\ninputs = [\n"]
    for item in items:
        value = repr(item) if use_repr else item
        lines.append(f"    {value},\n")
    lines.append("]\n\n")
    return "".join(lines)


def build_original_script(code_content, input_literals, model_footer, task_dir=None):
    func_name = get_entry_point(task_dir, code_content) if task_dir else get_first_function_name(code_content)
    if not func_name:
        raise ValueError("No function definition found in code.py")

    lines = [code_content, build_inputs_block(input_literals)]
    lines.append(ORIGINAL_OUTPUT_TEMPLATE.format(func_name=func_name))
    if model_footer:
        lines.append("\n")
        lines.append(model_footer)
    return "".join(lines)


def write_original_task(task_dir, model_footer):
    code_path = os.path.join(task_dir, "code.py")
    input_path = os.path.join(task_dir, "sample_code_inputs.txt")
    if not os.path.exists(code_path):
        return "missing_code"

    with open(code_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    script_content = build_original_script(code_content, read_input_literals(input_path), model_footer, task_dir)
    for output_name in ("sample_inputs.py", "sample_original.py"):
        with open(os.path.join(task_dir, output_name), "w", encoding="utf-8") as f:
            f.write(script_content)
    return "written"


def write_mutation_task(task_dir, transform_path, output_name, result_file):
    if not os.path.exists(transform_path):
        return "missing_transform"

    input_path = os.path.join(task_dir, "sample_code_inputs.txt")
    with open(transform_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    func_name = get_first_function_name(code_content, default="fun1")
    inputs = parse_input_lines(input_path)
    script_content = (
        code_content
        + build_inputs_block(inputs, use_repr=True)
        + MUTATION_OUTPUT_TEMPLATE.format(func_name=func_name, result_file=result_file)
    )

    with open(os.path.join(task_dir, output_name), "w", encoding="utf-8") as f:
        f.write(script_content)
    return "written"


def iter_task_dirs(base_dir=MBPP_DIR):
    for folder in sorted(os.listdir(str(base_dir))):
        task_dir = os.path.join(str(base_dir), folder)
        if os.path.isdir(task_dir):
            yield folder, task_dir


def splice_original(base_dir=MBPP_DIR):
    model_footer = read_model_footer()
    stats = {"written": 0, "missing": 0}
    for folder, task_dir in iter_task_dirs(base_dir):
        status = write_original_task(task_dir, model_footer)
        if status == "written":
            stats["written"] += 1
            print(f"[written] {folder}")
        else:
            stats["missing"] += 1
            print(f"[missing] {folder}: code.py")
    return stats


def splice_mutation(mode, base_dir=MBPP_DIR):
    if mode == "equivalent":
        transform_root = EQUIV_TRANSFORM
        output_name = "sample_inputs_equivalent.py"
        result_file = "sample_code_results_equivalent.txt"
    elif mode == "non_equivalent":
        transform_root = NON_EQUIV_TRANSFORM
        output_name = "sample_inputs_non_equivalent.py"
        result_file = "sample_code_results_non_equivalent.txt"
    else:
        raise ValueError(f"Unknown splice mode: {mode}")

    stats = {"written": 0, "missing": 0}
    for folder, task_dir in iter_task_dirs(base_dir):
        transform_path = os.path.join(str(transform_root), f"{folder}.py")
        status = write_mutation_task(task_dir, transform_path, output_name, result_file)
        if status == "written":
            stats["written"] += 1
            print(f"[written] {folder}")
        else:
            stats["missing"] += 1
            print(f"[missing] {folder}: {transform_path}")
    return stats


def splice_mode(mode, base_dir=MBPP_DIR):
    if mode == "original":
        return {"original": splice_original(base_dir)}
    if mode in ("equivalent", "non_equivalent"):
        return {mode: splice_mutation(mode, base_dir)}
    if mode == "all":
        return {
            "original": splice_original(base_dir),
            "equivalent": splice_mutation("equivalent", base_dir),
            "non_equivalent": splice_mutation("non_equivalent", base_dir),
        }
    raise ValueError(f"Unknown splice mode: {mode}")
