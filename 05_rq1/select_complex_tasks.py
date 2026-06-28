import argparse
import ast
import json
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import MBPP_DIR


def score_task(task_dir):
    code_path = task_dir / "code.py"
    input_path = task_dir / "sample_code_inputs.txt"
    if not code_path.exists() or not input_path.exists():
        return None
    inputs = input_path.read_text(encoding="utf-8").splitlines()
    if len([line for line in inputs if line.strip()]) != 10:
        return None
    code = code_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    nodes = list(ast.walk(tree))
    functions = [node.name for node in nodes if isinstance(node, ast.FunctionDef)]
    calls = [node.func.id for node in nodes if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    loops = sum(isinstance(node, (ast.For, ast.While)) for node in nodes)
    branches = sum(isinstance(node, ast.If) for node in nodes)
    recursion = sum(1 for function in functions for call in calls if call == function)
    input_chars = sum(len(line) for line in inputs)
    score = len(nodes) + 25 * loops + 20 * branches + 50 * recursion + input_chars // 200
    return {
        "task_id": task_dir.name,
        "score": score,
        "ast_nodes": len(nodes),
        "loops": loops,
        "branches": branches,
        "recursion_calls": recursion,
        "input_chars": input_chars,
    }


def main():
    parser = argparse.ArgumentParser(description="Select random complex tasks for generator smoke testing.")
    parser.add_argument("--task_root", default=str(MBPP_DIR))
    parser.add_argument("--top", type=int, default=80)
    parser.add_argument("--sample", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260625)
    args = parser.parse_args()

    rows = []
    for task_dir in Path(args.task_root).glob("task_*"):
        item = score_task(task_dir)
        if item:
            rows.append(item)
    rows = sorted(rows, key=lambda item: (-item["score"], item["task_id"]))
    pool = rows[: args.top]
    random.seed(args.seed)
    selected = random.sample(pool, min(args.sample, len(pool)))
    print(",".join(item["task_id"] for item in selected))
    print(json.dumps(selected, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
