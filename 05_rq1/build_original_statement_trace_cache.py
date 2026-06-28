import argparse
import ast
import json
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_splice"))

from audit_non_equiv_line_trace import (
    build_statement_line_map,
    call_args,
    compile_namespace,
    jsonable,
    read_input_lines,
    statement_trace,
    task_sort_key,
    trace_function_call,
)
from paths import MBPP_DIR, ROOT
from splice_utils import choose_callable_function, get_test_entry_name


DEFAULT_SUMMARY = ROOT / "reports" / "rq1_original_statement_trace_cache_summary.json"
CACHE_NAME = "original_statement_trace.jsonl"


def trace_function_call_statement_rle(namespace, filename, function_name, args, statement_map, max_events):
    trace = []
    trace_rle = []
    event_count = 0
    filename = str(filename)
    target = namespace[function_name]

    def append_key(key):
        if trace_rle and trace_rle[-1]["statement"] == key:
            trace_rle[-1]["count"] += 1
        else:
            trace_rle.append({"statement": key, "count": 1})
        trace.append(key)

    def tracer(frame, event, arg):
        nonlocal event_count
        if event != "line":
            return tracer
        if frame.f_code.co_filename != filename:
            return tracer
        if frame.f_code.co_name != function_name:
            return tracer
        event_count += 1
        if max_events and event_count > max_events:
            raise RuntimeError(f"line trace exceeded max_events={max_events}")
        append_key(statement_map.get(frame.f_lineno, f"unmapped:{frame.f_lineno}"))
        return tracer

    old_trace = sys.gettrace()
    sys.settrace(tracer)
    try:
        result = target(*args)
        return {
            "ok": True,
            "result": result,
            "result_text": str(result),
            "error": None,
            "statement_trace": trace,
            "statement_trace_rle": trace_rle,
            "trace_event_count": event_count,
        }
    except Exception as exc:
        return {
            "ok": False,
            "result": None,
            "result_text": None,
            "error": short_error(exc),
            "statement_trace": trace,
            "statement_trace_rle": trace_rle,
            "trace_event_count": event_count,
        }
    finally:
        sys.settrace(old_trace)


def short_error(exc):
    return "".join(traceback.format_exception_only(type(exc), exc)).strip()


def parse_inputs(input_lines):
    return [ast.literal_eval(line) for line in input_lines]


def build_cache_for_task(task_dir, max_events):
    task_id = task_dir.name
    source_path = task_dir / "code.py"
    input_path = task_dir / "sample_code_inputs.txt"
    cache_path = task_dir / CACHE_NAME

    input_lines = read_input_lines(input_path)
    if input_lines is None:
        return {
            "task_id": task_id,
            "status": "missing_inputs",
            "input_count": 0,
            "cache_path": str(cache_path.resolve()),
            "error": str(input_path),
        }
    if not source_path.exists():
        return {
            "task_id": task_id,
            "status": "missing_code",
            "input_count": len(input_lines),
            "cache_path": str(cache_path.resolve()),
            "error": str(source_path),
        }

    source = source_path.read_text(encoding="utf-8")
    try:
        parsed_inputs = parse_inputs(input_lines)
        function_name = choose_callable_function(
            source,
            parsed_inputs,
            preferred_name=get_test_entry_name(str(task_dir)),
        )
        namespace = compile_namespace(source, source_path.resolve())
        statement_map = build_statement_line_map(source, function_name)
    except Exception as exc:
        return {
            "task_id": task_id,
            "status": "setup_error",
            "input_count": len(input_lines),
            "cache_path": str(cache_path.resolve()),
            "error": short_error(exc),
        }

    records = []
    failed_records = []
    for input_index, (input_text, input_value) in enumerate(zip(input_lines, parsed_inputs), start=1):
        run = trace_function_call_statement_rle(
            namespace,
            source_path.resolve(),
            function_name,
            call_args(input_value),
            statement_map,
            max_events,
        )
        if not run["ok"]:
            failed_records.append(
                {
                    "input_index": input_index,
                    "input": input_text,
                    "error": run["error"],
                    "trace_event_count": run["trace_event_count"],
                    "partial_statement_trace_rle": run["statement_trace_rle"],
                }
            )
            continue

        records.append(
            {
                "task_id": task_id,
                "input_index": input_index,
                "input": input_text,
                "function_name": function_name,
                "original_output": jsonable(run["result"]),
                "original_output_text": run["result_text"],
                "statement_trace": run["statement_trace"],
                "statement_trace_rle": run["statement_trace_rle"],
                "trace_event_count": run["trace_event_count"],
            }
        )

    with cache_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    status = "written" if not failed_records else "partial"
    return {
        "task_id": task_id,
        "status": status,
        "input_count": len(input_lines),
        "cache_records": len(records),
        "cache_path": str(cache_path.resolve()),
        "failed_records": failed_records,
    }


def iter_task_dirs(task_root, task=None, tasks=None, limit=None):
    if tasks:
        task_dirs = [task_root / task_id for task_id in tasks]
    elif task:
        task_dirs = [task_root / task]
    else:
        task_dirs = sorted((path for path in task_root.glob("task_*") if path.is_dir()), key=task_sort_key)
    if limit is not None:
        task_dirs = task_dirs[:limit]
    return task_dirs


def summarize(records, expected_tasks, expected_inputs_per_task):
    status_counts = {}
    wrong_input_counts = {}
    total_cases = 0
    for record in records:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
        input_count = record.get("input_count", 0)
        total_cases += record.get("cache_records", 0)
        if input_count != expected_inputs_per_task:
            wrong_input_counts[record["task_id"]] = input_count

    return {
        "expected_tasks": expected_tasks,
        "tasks_seen": len(records),
        "expected_inputs_per_task": expected_inputs_per_task,
        "natural_total_input_cases": total_cases,
        "status_counts": status_counts,
        "tasks_with_less_or_more_than_expected_inputs": wrong_input_counts,
        "cache_complete_for_available_inputs": status_counts == {"written": len(records)},
    }


def main():
    parser = argparse.ArgumentParser(description="Build per-task original statement trace cache JSONL files.")
    parser.add_argument("--task_root", default=str(MBPP_DIR))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--expected_tasks", type=int, default=378)
    parser.add_argument("--expected_inputs_per_task", type=int, default=10)
    parser.add_argument("--max_events", type=int, default=0, help="0 means no trace event limit")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task")
    parser.add_argument("--tasks", help="Comma-separated task ids")
    args = parser.parse_args()

    task_root = Path(args.task_root)
    selected_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()] if args.tasks else None
    records = []
    for task_dir in iter_task_dirs(task_root, args.task, selected_tasks, args.limit):
        record = build_cache_for_task(task_dir, args.max_events)
        records.append(record)
        print(
            f"[{record['status']}] {record['task_id']} "
            f"inputs={record.get('input_count', 0)} cache_records={record.get('cache_records', 0)}"
        )

    expected_tasks = len(records) if args.limit or args.task or selected_tasks else args.expected_tasks
    summary = summarize(records, expected_tasks, args.expected_inputs_per_task)
    summary.update(
        {
            "command": " ".join(sys.argv),
            "purpose": (
                "Build local cached original outputs and original statement traces for every available RQ1 input. "
                "Each task directory receives original_statement_trace.jsonl with one JSON object per input."
            ),
            "task_root": str(task_root.resolve()),
            "cache_file_name": CACHE_NAME,
            "records": records,
        }
    )

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== Original Statement Trace Cache =====")
    print(f"Summary: {summary_path.resolve()}")
    print(f"Natural total input cases: {summary['natural_total_input_cases']}")
    print(f"Status counts: {summary['status_counts']}")
    if summary["tasks_with_less_or_more_than_expected_inputs"]:
        print(f"Tasks with non-10 input counts: {summary['tasks_with_less_or_more_than_expected_inputs']}")


if __name__ == "__main__":
    main()
