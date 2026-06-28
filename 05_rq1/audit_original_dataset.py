import argparse
import ast
import json
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_splice"))

from paths import MBPP_DIR, ROOT
from splice_utils import choose_callable_function, get_test_entry_name


DEFAULT_SUMMARY = ROOT / "reports" / "rq1_original_dataset_audit_summary.json"
DEFAULT_JSONL = ROOT / "reports" / "rq1_original_dataset_audit.jsonl"


def task_sort_key(path):
    try:
        return int(path.name.rsplit("_", 1)[1])
    except Exception:
        return path.name


def short_error(exc):
    return "".join(traceback.format_exception_only(type(exc), exc)).strip()


def read_input_lines(path):
    if not path.exists():
        return None
    return [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_input(text):
    return ast.literal_eval(text)


def call_args(value):
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def compile_namespace(code_text, filename):
    namespace = {"__file__": str(filename), "__name__": "__rq1_original_audit__"}
    exec(compile(code_text, str(filename), "exec"), namespace)
    return namespace


def jsonable(value):
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except Exception:
        return repr(value)


def audit_task(task_dir, expected_inputs_per_task):
    task_id = task_dir.name
    code_path = task_dir / "code.py"
    input_path = task_dir / "sample_code_inputs.txt"

    input_lines = read_input_lines(input_path)
    if input_lines is None:
        return [
            {
                "task_id": task_id,
                "input_index": index,
                "status": "missing_inputs_file",
                "input": None,
                "error": str(input_path),
            }
            for index in range(1, expected_inputs_per_task + 1)
        ]

    if not code_path.exists():
        return [
            {
                "task_id": task_id,
                "input_index": index,
                "status": "missing_code_file",
                "input": input_lines[index - 1] if index <= len(input_lines) else None,
                "error": str(code_path),
            }
            for index in range(1, max(len(input_lines), expected_inputs_per_task) + 1)
        ]

    code_text = code_path.read_text(encoding="utf-8")
    parsed_inputs = []
    parse_errors = {}
    for index, input_text in enumerate(input_lines):
        try:
            parsed_inputs.append(parse_input(input_text))
        except Exception as exc:
            parsed_inputs.append(None)
            parse_errors[index] = short_error(exc)

    try:
        func_name = choose_callable_function(
            code_text,
            parsed_inputs,
            preferred_name=get_test_entry_name(str(task_dir)),
        )
        namespace = compile_namespace(code_text, code_path.resolve())
        target = namespace[func_name]
    except Exception as exc:
        return [
            {
                "task_id": task_id,
                "input_index": index,
                "status": "setup_error",
                "input": input_lines[index - 1] if index <= len(input_lines) else None,
                "error": short_error(exc),
            }
            for index in range(1, max(len(input_lines), expected_inputs_per_task) + 1)
        ]

    records = []
    for index in range(1, expected_inputs_per_task + 1):
        if index > len(input_lines):
            records.append(
                {
                    "task_id": task_id,
                    "input_index": index,
                    "status": "missing_input_slot",
                    "input": None,
                    "error": f"Expected input {index}, but {input_path} has only {len(input_lines)} inputs.",
                }
            )
            continue

        input_text = input_lines[index - 1]
        if index - 1 in parse_errors:
            records.append(
                {
                    "task_id": task_id,
                    "input_index": index,
                    "status": "input_parse_error",
                    "input": input_text,
                    "error": parse_errors[index - 1],
                }
            )
            continue

        try:
            result = target(*call_args(parsed_inputs[index - 1]))
            records.append(
                {
                    "task_id": task_id,
                    "input_index": index,
                    "status": "pass",
                    "input": input_text,
                    "output": jsonable(result),
                    "output_text": str(result),
                    "error": None,
                }
            )
        except Exception as exc:
            records.append(
                {
                    "task_id": task_id,
                    "input_index": index,
                    "status": "runtime_error",
                    "input": input_text,
                    "error": short_error(exc),
                }
            )

    return records


def main():
    parser = argparse.ArgumentParser(description="Audit original RQ1 dataset inputs and outputs.")
    parser.add_argument("--task_root", default=str(MBPP_DIR))
    parser.add_argument("--expected_tasks", type=int, default=378)
    parser.add_argument("--expected_inputs_per_task", type=int, default=10)
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    args = parser.parse_args()

    task_root = Path(args.task_root)
    task_dirs = sorted((path for path in task_root.glob("task_*") if path.is_dir()), key=task_sort_key)
    records = []
    input_counts = {}
    for task_dir in task_dirs:
        input_lines = read_input_lines(task_dir / "sample_code_inputs.txt")
        input_counts[task_dir.name] = 0 if input_lines is None else len(input_lines)
        task_records = audit_task(task_dir, args.expected_inputs_per_task)
        records.extend(task_records)
        print(f"[audited] {task_dir.name}: inputs={input_counts[task_dir.name]}, records={len(task_records)}")

    status_counts = {}
    for record in records:
        status = record["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    wrong_input_counts = {
        task_id: count
        for task_id, count in input_counts.items()
        if count != args.expected_inputs_per_task
    }
    expected_total = args.expected_tasks * args.expected_inputs_per_task
    summary = {
        "task_root": str(task_root.resolve()),
        "expected_tasks": args.expected_tasks,
        "tasks_seen": len(task_dirs),
        "expected_inputs_per_task": args.expected_inputs_per_task,
        "expected_total_inputs": expected_total,
        "total_records": len(records),
        "status_counts": status_counts,
        "pass_count": status_counts.get("pass", 0),
        "dataset_complete": (
            len(task_dirs) == args.expected_tasks
            and len(records) == expected_total
            and status_counts.get("pass", 0) == expected_total
            and not wrong_input_counts
        ),
        "tasks_with_wrong_input_count": wrong_input_counts,
        "failed_cases": [
            record
            for record in records
            if record["status"] != "pass"
        ],
    }

    jsonl_path = Path(args.jsonl)
    summary_path = Path(args.summary)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== RQ1 Original Dataset Audit =====")
    print(f"JSONL report: {jsonl_path.resolve()}")
    print(f"Summary report: {summary_path.resolve()}")
    print(f"Dataset complete: {summary['dataset_complete']}")
    print(f"Pass: {summary['pass_count']} / {expected_total}")
    print(f"Status counts: {status_counts}")
    if wrong_input_counts:
        print(f"Tasks with wrong input count: {wrong_input_counts}")


if __name__ == "__main__":
    main()
