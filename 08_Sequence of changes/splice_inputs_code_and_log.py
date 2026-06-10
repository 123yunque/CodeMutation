import argparse
import ast
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT / "output_mbppplus_new"

MODE_CONFIGS = {
    "original": {
        "source_file": "sample_inputs.py",
        "input_prefix": "original",
    },
    "equivalent": {
        "source_file": "sample_inputs_equivalent.py",
        "input_prefix": "equivalent",
    },
    "non_equivalent": {
        "source_file": "sample_inputs_non_equivalent.py",
        "input_prefix": "non_equivalent",
    },
}


def find_inputs_assignment(source):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "inputs":
                    return node.lineno, node.end_lineno
    raise ValueError("missing top-level inputs assignment")


def split_source_around_inputs(source):
    lines = source.splitlines(keepends=True)
    start_line, end_line = find_inputs_assignment(source)
    code_content = "".join(lines[: start_line - 1]).rstrip() + "\n\n"
    execution_tail = "".join(lines[end_line:]).lstrip()
    return code_content, execution_tail


def read_input_literals(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def build_inputs_block(input_literals):
    lines = ["inputs = [\n"]
    for item in input_literals:
        value = item.rstrip(",")
        lines.append(f"    {value},\n")
    lines.append("]\n\n")
    return "".join(lines)


def generate_mode(mode, limit=None, task=None):
    config = MODE_CONFIGS[mode]
    source_name = config["source_file"]
    input_prefix = config["input_prefix"]
    stats = {"written": 0, "missing_source": 0, "missing_inputs": 0, "failed": 0}

    if task:
        task_dirs = [BASE_DIR / task]
    else:
        task_dirs = sorted(path for path in BASE_DIR.glob("task_*") if path.is_dir())
    if limit is not None:
        task_dirs = task_dirs[:limit]

    for task_dir in task_dirs:
        if not task_dir.is_dir():
            stats["missing_source"] += 1
            print(f"[missing-task] {task_dir.name}")
            continue

        source_path = task_dir / source_name
        if not source_path.exists():
            stats["missing_source"] += 1
            print(f"[missing-source] {task_dir.name}: {source_name}")
            continue

        try:
            source = source_path.read_text(encoding="utf-8")
            code_content, execution_tail = split_source_around_inputs(source)
        except Exception as exc:
            stats["failed"] += 1
            print(f"[failed] {task_dir.name}: cannot split {source_name}: {exc}")
            continue

        for status in ("correct", "error"):
            input_path = task_dir / f"{input_prefix}_{status}_inputs.txt"
            input_literals = read_input_literals(input_path)
            if input_literals is None:
                stats["missing_inputs"] += 1
                print(f"[missing-inputs] {task_dir.name}: {input_path.name}")
                continue

            output_path = task_dir / f"sample_{input_prefix}_{status}.py"
            output_path.write_text(
                code_content + build_inputs_block(input_literals) + execution_tail,
                encoding="utf-8",
            )
            stats["written"] += 1
            print(f"[written] {task_dir.name}: {output_path.name}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Build RQ2 correct/error scripts without truncating execution logic.")
    parser.add_argument("--mode", choices=("all",) + tuple(MODE_CONFIGS), default="all")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task", help="Optional task folder name, for example task_100")
    args = parser.parse_args()

    modes = tuple(MODE_CONFIGS) if args.mode == "all" else (args.mode,)
    for mode in modes:
        stats = generate_mode(mode, limit=args.limit, task=args.task)
        print(
            f"Done {mode}. written={stats['written']}, "
            f"missing_source={stats['missing_source']}, "
            f"missing_inputs={stats['missing_inputs']}, failed={stats['failed']}"
        )


if __name__ == "__main__":
    main()
