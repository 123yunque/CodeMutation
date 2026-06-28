import argparse
import ast
import json
import os
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_splice"))

from paths import MBPP_DIR, NON_EQUIV_TRANSFORM, ROOT
from splice_utils import choose_callable_function, get_test_entry_name


DEFAULT_JSONL = ROOT / "reports" / "rq1_non_equiv_line_trace_audit_mbppplus.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "rq1_non_equiv_line_trace_audit_mbppplus_summary.json"


def task_sort_key(path):
    name = path.name if hasattr(path, "name") else str(path)
    try:
        return int(name.rsplit("_", 1)[1])
    except Exception:
        return name


def read_input_lines(path):
    if not path.exists():
        return None
    return [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_input(input_text):
    return ast.literal_eval(input_text)


def call_args(input_value):
    if isinstance(input_value, (list, tuple)):
        return tuple(input_value)
    return (input_value,)


def jsonable(value):
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except Exception:
        return repr(value)


def short_error(exc):
    return "".join(traceback.format_exception_only(type(exc), exc)).strip()


def compile_namespace(code_text, filename):
    namespace = {"__file__": str(filename), "__name__": "__rq1_trace_audit__"}
    code = compile(code_text, str(filename), "exec")
    exec(code, namespace)
    return namespace


def trace_function_call(namespace, filename, function_name, args, max_events):
    trace = []
    filename = str(filename)
    target = namespace[function_name]

    def tracer(frame, event, arg):
        if event != "line":
            return tracer
        if frame.f_code.co_filename != filename:
            return tracer
        if frame.f_code.co_name != function_name:
            return tracer
        trace.append(frame.f_lineno)
        if len(trace) > max_events:
            raise RuntimeError(f"line trace exceeded max_events={max_events}")
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
            "trace": trace,
        }
    except Exception as exc:
        return {
            "ok": False,
            "result": None,
            "result_text": None,
            "error": short_error(exc),
            "trace": trace,
        }
    finally:
        sys.settrace(old_trace)


def relative_trace(trace, function_start_line):
    return [line - function_start_line + 1 for line in trace]


def get_function_start_line(code_text, function_name):
    tree = ast.parse(code_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node.lineno
    return None


def build_statement_line_map(code_text, function_name):
    tree = ast.parse(code_text)
    function_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            function_node = node
            break
    if function_node is None:
        return {}

    line_map = {}

    def mark_statement(stmt, key):
        end_line = getattr(stmt, "end_lineno", stmt.lineno)
        for line in range(stmt.lineno, end_line + 1):
            line_map[line] = key

    def walk_statements(statements, prefix):
        for index, stmt in enumerate(statements):
            key = f"{prefix}.{index}:{type(stmt).__name__}"
            mark_statement(stmt, key)

            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While, ast.If, ast.With, ast.AsyncWith)):
                walk_statements(stmt.body, f"{key}.body")
                walk_statements(stmt.orelse, f"{key}.orelse")
            elif isinstance(stmt, ast.Try):
                walk_statements(stmt.body, f"{key}.body")
                for handler_index, handler in enumerate(stmt.handlers):
                    walk_statements(handler.body, f"{key}.handler{handler_index}")
                walk_statements(stmt.orelse, f"{key}.orelse")
                walk_statements(stmt.finalbody, f"{key}.finalbody")
            elif hasattr(ast, "Match") and isinstance(stmt, ast.Match):
                for case_index, case in enumerate(stmt.cases):
                    walk_statements(case.body, f"{key}.case{case_index}")

    walk_statements(function_node.body, "body")
    return line_map


def statement_trace(trace, line_map):
    return [line_map.get(line, f"unmapped:{line}") for line in trace]


def load_llm_lines(llm_output_dir, task_id):
    if not llm_output_dir:
        return None
    path = Path(llm_output_dir) / f"{task_id}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").splitlines()


def classify_llm_answer(llm_answer, original_text, mutated_text):
    if llm_answer is None:
        return "missing_llm_answer"
    if llm_answer == mutated_text:
        return "mutated_correct"
    if llm_answer == original_text and original_text != mutated_text:
        return "original_leak"
    return "other_error"


def build_missing_record(task_id, input_index, input_text, status, reason):
    return {
        "task_id": task_id,
        "input_index": input_index,
        "input": input_text,
        "status": status,
        "reason": reason,
    }


def audit_task(task_dir, transform_root, max_events, llm_output_dir):
    task_id = task_dir.name
    original_path = task_dir / "code.py"
    mutated_path = transform_root / f"{task_id}.py"
    input_path = task_dir / "sample_code_inputs.txt"

    input_lines = read_input_lines(input_path)
    if input_lines is None:
        return [build_missing_record(task_id, None, None, "missing_inputs", str(input_path))]

    if not original_path.exists():
        return [
            build_missing_record(task_id, index + 1, input_text, "missing_original_code", str(original_path))
            for index, input_text in enumerate(input_lines)
        ]

    if not mutated_path.exists():
        return [
            build_missing_record(task_id, index + 1, input_text, "missing_mutated_code", str(mutated_path))
            for index, input_text in enumerate(input_lines)
        ]

    original_code = original_path.read_text(encoding="utf-8")
    mutated_code = mutated_path.read_text(encoding="utf-8")
    original_lines = original_code.splitlines()
    mutated_lines = mutated_code.splitlines()
    line_count_same = len(original_lines) == len(mutated_lines)

    preferred_name = get_test_entry_name(str(task_dir))
    parsed_inputs = []
    parse_errors = {}
    for index, input_text in enumerate(input_lines):
        try:
            parsed_inputs.append(parse_input(input_text))
        except Exception as exc:
            parsed_inputs.append(None)
            parse_errors[index] = short_error(exc)

    records = []
    try:
        original_func = choose_callable_function(original_code, parsed_inputs, preferred_name=preferred_name)
        mutated_func = choose_callable_function(mutated_code, parsed_inputs, preferred_name=preferred_name)
        original_start = get_function_start_line(original_code, original_func)
        mutated_start = get_function_start_line(mutated_code, mutated_func)
        original_statement_map = build_statement_line_map(original_code, original_func)
        mutated_statement_map = build_statement_line_map(mutated_code, mutated_func)
        original_ns = compile_namespace(original_code, original_path.resolve())
        mutated_ns = compile_namespace(mutated_code, mutated_path.resolve())
    except Exception as exc:
        reason = short_error(exc)
        return [
            build_missing_record(task_id, index + 1, input_text, "setup_error", reason)
            for index, input_text in enumerate(input_lines)
        ]

    llm_lines = load_llm_lines(llm_output_dir, task_id)

    for index, input_text in enumerate(input_lines):
        input_index = index + 1
        if index in parse_errors:
            records.append(build_missing_record(task_id, input_index, input_text, "input_parse_error", parse_errors[index]))
            continue

        args = call_args(parsed_inputs[index])
        original = trace_function_call(original_ns, original_path.resolve(), original_func, args, max_events)
        mutated = trace_function_call(mutated_ns, mutated_path.resolve(), mutated_func, args, max_events)

        same_line_trace = original["trace"] == mutated["trace"]
        original_relative = relative_trace(original["trace"], original_start) if original_start else []
        mutated_relative = relative_trace(mutated["trace"], mutated_start) if mutated_start else []
        same_relative_trace = original_relative == mutated_relative
        original_statement_trace = statement_trace(original["trace"], original_statement_map)
        mutated_statement_trace = statement_trace(mutated["trace"], mutated_statement_map)
        same_statement_trace = original_statement_trace == mutated_statement_trace
        output_changed = original["ok"] and mutated["ok"] and original["result_text"] != mutated["result_text"]
        function_name_same = original_func == mutated_func

        if not original["ok"]:
            status = "original_runtime_error"
        elif not mutated["ok"]:
            status = "mutated_runtime_error"
        elif not function_name_same:
            status = "function_name_changed"
        elif not output_changed:
            status = "same_output"
        elif not same_statement_trace:
            status = "statement_trace_diff"
        else:
            status = "pass"

        llm_answer = llm_lines[index] if llm_lines and index < len(llm_lines) else None
        llm_classification = (
            classify_llm_answer(llm_answer, original["result_text"], mutated["result_text"])
            if llm_output_dir
            else None
        )

        records.append(
            {
                "task_id": task_id,
                "input_index": input_index,
                "input": input_text,
                "status": status,
                "original_function": original_func,
                "mutated_function": mutated_func,
                "function_name_same": function_name_same,
                "original_line_count": len(original_lines),
                "mutated_line_count": len(mutated_lines),
                "line_count_same": line_count_same,
                "original_output": jsonable(original["result"]),
                "mutated_output": jsonable(mutated["result"]),
                "original_output_text": original["result_text"],
                "mutated_output_text": mutated["result_text"],
                "original_error": original["error"],
                "mutated_error": mutated["error"],
                "output_changed": output_changed,
                "original_trace": original["trace"],
                "mutated_trace": mutated["trace"],
                "same_line_trace": same_line_trace,
                "original_relative_trace": original_relative,
                "mutated_relative_trace": mutated_relative,
                "same_relative_trace": same_relative_trace,
                "original_statement_trace": original_statement_trace,
                "mutated_statement_trace": mutated_statement_trace,
                "same_statement_trace": same_statement_trace,
                "llm_answer": llm_answer,
                "llm_classification": llm_classification,
            }
        )

    return records


def summarize(records, task_input_counts, expected_tasks, expected_inputs_per_task, command, jsonl_path):
    status_counts = {}
    llm_counts = {}
    for record in records:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
        llm_class = record.get("llm_classification")
        if llm_class:
            llm_counts[llm_class] = llm_counts.get(llm_class, 0) + 1

    expected_total = expected_tasks * expected_inputs_per_task
    wrong_input_counts = {
        task_id: count
        for task_id, count in task_input_counts.items()
        if count != expected_inputs_per_task
    }
    total_records = len(records)
    pass_count = status_counts.get("pass", 0)
    return {
        "command": command,
        "purpose": (
            "Audit RQ1 non-equivalent mutations at input granularity. "
            "Each JSONL row stores one input case, local outputs, line traces, and pass/fail classification."
        ),
        "jsonl_report": str(Path(jsonl_path).resolve()),
        "expected_tasks": expected_tasks,
        "expected_inputs_per_task": expected_inputs_per_task,
        "expected_total_inputs": expected_total,
        "tasks_seen": len(task_input_counts),
        "total_input_records": total_records,
        "dataset_complete": (
            len(task_input_counts) == expected_tasks
            and total_records == expected_total
            and not wrong_input_counts
        ),
        "tasks_with_wrong_input_count": wrong_input_counts,
        "status_counts": status_counts,
        "pass_count": pass_count,
        "pass_rate": round(pass_count / total_records, 6) if total_records else 0.0,
        "output_changed_count": sum(1 for record in records if record.get("output_changed")),
        "same_line_trace_count": sum(1 for record in records if record.get("same_line_trace")),
        "same_relative_trace_count": sum(1 for record in records if record.get("same_relative_trace")),
        "same_statement_trace_count": sum(1 for record in records if record.get("same_statement_trace")),
        "llm_classification_counts": llm_counts,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit RQ1 non-equivalent mutations with per-input line traces.")
    parser.add_argument("--task_root", default=str(MBPP_DIR), help="Task directory root")
    parser.add_argument("--transform_root", default=str(NON_EQUIV_TRANSFORM), help="Non-equivalent transform root")
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL), help="Output JSONL path")
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY), help="Output summary JSON path")
    parser.add_argument("--expected_tasks", type=int, default=378)
    parser.add_argument("--expected_inputs_per_task", type=int, default=10)
    parser.add_argument("--max_events", type=int, default=5000000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task", help="Audit one task id, for example task_100")
    parser.add_argument("--tasks", help="Comma-separated task ids, for example task_65,task_84")
    parser.add_argument("--llm_output_dir", help="Optional RQ1 LLM output directory for original-leak classification")
    parser.add_argument(
        "--no_emit_missing_input_slots",
        action="store_true",
        help="Do not emit JSONL placeholder rows for missing expected input positions.",
    )
    args = parser.parse_args()

    task_root = Path(args.task_root)
    transform_root = Path(args.transform_root)
    jsonl_path = Path(args.jsonl)
    summary_path = Path(args.summary)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    selected_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()] if args.tasks else None

    if selected_tasks:
        task_dirs = [task_root / task_id for task_id in selected_tasks]
    elif args.task:
        task_dirs = [task_root / args.task]
    else:
        task_dirs = sorted((path for path in task_root.glob("task_*") if path.is_dir()), key=task_sort_key)
    if args.limit is not None:
        task_dirs = task_dirs[: args.limit]

    all_records = []
    task_input_counts = {}
    with jsonl_path.open("w", encoding="utf-8") as out:
        for task_dir in task_dirs:
            input_lines = read_input_lines(task_dir / "sample_code_inputs.txt")
            task_input_counts[task_dir.name] = len(input_lines) if input_lines is not None else 0
            records = audit_task(task_dir, transform_root, args.max_events, args.llm_output_dir)
            if (
                not args.no_emit_missing_input_slots
                and input_lines is not None
                and len(input_lines) < args.expected_inputs_per_task
            ):
                for missing_index in range(len(input_lines) + 1, args.expected_inputs_per_task + 1):
                    records.append(
                        build_missing_record(
                            task_dir.name,
                            missing_index,
                            None,
                            "missing_input_slot",
                            f"Expected input {missing_index}, but {task_dir / 'sample_code_inputs.txt'} has only {len(input_lines)} inputs.",
                        )
                    )
            for record in records:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            all_records.extend(records)
            print(f"[audited] {task_dir.name}: inputs={task_input_counts[task_dir.name]}, records={len(records)}")

    command = " ".join(sys.argv)
    summary = summarize(
        all_records,
        task_input_counts,
        args.expected_tasks if args.limit is None and not args.task else len(task_dirs),
        args.expected_inputs_per_task,
        command,
        jsonl_path,
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== RQ1 Non-Equivalent Line Trace Audit =====")
    print(f"JSONL report: {jsonl_path.resolve()}")
    print(f"Summary report: {summary_path.resolve()}")
    print(f"Dataset complete: {summary['dataset_complete']}")
    print(f"Total input records: {summary['total_input_records']} / {summary['expected_total_inputs']}")
    print(f"Pass: {summary['pass_count']} ({summary['pass_rate']:.2%})")
    print(f"Status counts: {summary['status_counts']}")
    if summary["llm_classification_counts"]:
        print(f"LLM classification counts: {summary['llm_classification_counts']}")


if __name__ == "__main__":
    main()
