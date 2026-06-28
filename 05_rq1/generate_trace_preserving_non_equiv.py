import argparse
import ast
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_splice"))

from audit_non_equiv_line_trace import (
    build_statement_line_map,
    call_args,
    compile_namespace,
    jsonable,
    read_input_lines,
    relative_trace,
    short_error,
    statement_trace,
    task_sort_key,
    trace_function_call,
)
from paths import MBPP_DIR, ROOT
from splice_utils import choose_callable_function, get_test_entry_name


DEFAULT_OUTPUT_DIR = ROOT / "non_equivalent_transform_trace_preserving"
DEFAULT_REPORT = ROOT / "reports" / "rq1_trace_preserving_mutation_generation.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "rq1_trace_preserving_mutation_generation_summary.json"


class RiskyNameCollector(ast.NodeVisitor):
    def __init__(self):
        self.names = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.names.add(node.id)


def collect_risky_names(tree):
    risky = set()

    def add_from(node):
        collector = RiskyNameCollector()
        collector.visit(node)
        risky.update(collector.names)

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While)):
            add_from(node.test)
        elif isinstance(node, ast.For):
            add_from(node.iter)
        elif isinstance(node, ast.Subscript):
            add_from(node.slice)
    return risky


def target_names(target):
    names = set()
    for node in ast.walk(target):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
    return names


class MutationPointCollector(ast.NodeVisitor):
    def __init__(self, risky_names=None):
        self.points = []
        self.risky_names = risky_names or set()

    def visit_If(self, node):
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_While(self, node):
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_For(self, node):
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Return(self, node):
        if node.value is not None:
            replacements = expr_replacements()
            self.points.append({"kind": "return_expr", "line": node.lineno, "replacements": replacements})
            self.visit(node.value)

    def visit_Assign(self, node):
        assigned = set()
        for target in node.targets:
            assigned.update(target_names(target))
        if assigned & self.risky_names:
            return
        if node.value is not None:
            replacements = expr_replacements()
            self.points.append({"kind": "assign_expr", "line": node.lineno, "replacements": replacements})
            self.visit(node.value)

    def visit_AugAssign(self, node):
        if target_names(node.target) & self.risky_names:
            return
        replacements = augop_replacements(node.op)
        if replacements:
            self.points.append({"kind": "aug_op", "line": node.lineno, "replacements": replacements})
        self.visit(node.value)

    def visit_Compare(self, node):
        for index, op in enumerate(node.ops):
            replacements = compare_replacements(op)
            if replacements:
                self.points.append({"kind": "compare_op", "line": node.lineno, "op_index": index, "replacements": replacements})
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        replacements = bool_replacements(node.op)
        if replacements:
            self.points.append({"kind": "bool_op", "line": node.lineno, "replacements": replacements})
        self.generic_visit(node)

    def visit_BinOp(self, node):
        replacements = binop_replacements(node.op)
        if replacements:
            self.points.append({"kind": "bin_op", "line": node.lineno, "replacements": replacements})
        self.generic_visit(node)

    def visit_Attribute(self, node):
        replacements = attribute_replacements(node.attr)
        if replacements:
            self.points.append({"kind": "attribute", "line": node.lineno, "attr": node.attr, "replacements": replacements})
        self.generic_visit(node)

    def visit_Constant(self, node):
        replacements = constant_replacements(node.value)
        if replacements:
            self.points.append({"kind": "constant", "line": node.lineno, "value": node.value, "replacements": replacements})


class ApplyMutation(ast.NodeTransformer):
    def __init__(self, target_index, target_kind, replacement, risky_names=None):
        self.target_index = target_index
        self.target_kind = target_kind
        self.replacement = replacement
        self.current_index = -1
        self.applied = False
        self.risky_names = risky_names or set()

    def _next(self, kind):
        self.current_index += 1
        return self.current_index == self.target_index and self.target_kind == kind

    def visit_If(self, node):
        node.body = [self.visit(stmt) for stmt in node.body]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        return node

    def visit_While(self, node):
        node.body = [self.visit(stmt) for stmt in node.body]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        return node

    def visit_For(self, node):
        node.body = [self.visit(stmt) for stmt in node.body]
        node.orelse = [self.visit(stmt) for stmt in node.orelse]
        return node

    def visit_Return(self, node):
        if node.value is not None and self._next("return_expr"):
            node.value = apply_expr_replacement(node.value, self.replacement)
            self.applied = True
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

    def visit_Assign(self, node):
        assigned = set()
        for target in node.targets:
            assigned.update(target_names(target))
        if assigned & self.risky_names:
            return node
        if node.value is not None and self._next("assign_expr"):
            node.value = apply_expr_replacement(node.value, self.replacement)
            self.applied = True
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

    def visit_AugAssign(self, node):
        if target_names(node.target) & self.risky_names:
            return node
        if augop_replacements(node.op) and self._next("aug_op"):
            node.op = self.replacement()
            self.applied = True
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

    def visit_Compare(self, node):
        for index, op in enumerate(node.ops):
            if compare_replacements(op) and self._next("compare_op"):
                node.ops[index] = self.replacement()
                self.applied = True
                self.generic_visit(node)
                return node
        self.generic_visit(node)
        return node

    def visit_BoolOp(self, node):
        if bool_replacements(node.op) and self._next("bool_op"):
            node.op = self.replacement()
            self.applied = True
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

    def visit_BinOp(self, node):
        if binop_replacements(node.op) and self._next("bin_op"):
            node.op = self.replacement()
            self.applied = True
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node):
        if attribute_replacements(node.attr) and self._next("attribute"):
            node.attr = self.replacement
            self.applied = True
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

    def visit_Constant(self, node):
        if constant_replacements(node.value) and self._next("constant"):
            self.applied = True
            return ast.copy_location(ast.Constant(value=self.replacement), node)
        return node


def compare_replacements(op):
    table = {
        ast.Lt: [ast.LtE, ast.Gt, ast.GtE, ast.NotEq],
        ast.LtE: [ast.Lt, ast.Gt, ast.GtE, ast.NotEq],
        ast.Gt: [ast.GtE, ast.Lt, ast.LtE, ast.NotEq],
        ast.GtE: [ast.Gt, ast.Lt, ast.LtE, ast.NotEq],
        ast.Eq: [ast.NotEq],
        ast.NotEq: [ast.Eq],
        ast.Is: [ast.IsNot],
        ast.IsNot: [ast.Is],
        ast.In: [ast.NotIn],
        ast.NotIn: [ast.In],
    }
    return table.get(type(op), [])


def bool_replacements(op):
    if isinstance(op, ast.And):
        return [ast.Or]
    if isinstance(op, ast.Or):
        return [ast.And]
    return []


def binop_replacements(op):
    table = {
        ast.Add: [ast.Sub],
        ast.Sub: [ast.Add],
        ast.Mult: [ast.FloorDiv, ast.Add],
        ast.FloorDiv: [ast.Mult, ast.Sub],
        ast.Mod: [ast.Add, ast.Sub],
        ast.Pow: [ast.Mult],
        ast.BitAnd: [ast.BitOr, ast.BitXor],
        ast.BitOr: [ast.BitAnd, ast.BitXor],
        ast.BitXor: [ast.BitAnd, ast.BitOr],
        ast.LShift: [ast.RShift],
        ast.RShift: [ast.LShift],
    }
    return table.get(type(op), [])


def augop_replacements(op):
    return binop_replacements(op)


def expr_replacements():
    return ["add_one", "sub_one", "negate", "logical_not"]


def apply_expr_replacement(expr, replacement):
    expr = ast.copy_location(expr, expr)
    if replacement == "add_one":
        return ast.copy_location(ast.BinOp(left=expr, op=ast.Add(), right=ast.Constant(value=1)), expr)
    if replacement == "sub_one":
        return ast.copy_location(ast.BinOp(left=expr, op=ast.Sub(), right=ast.Constant(value=1)), expr)
    if replacement == "negate":
        return ast.copy_location(ast.UnaryOp(op=ast.USub(), operand=expr), expr)
    if replacement == "logical_not":
        return ast.copy_location(ast.UnaryOp(op=ast.Not(), operand=expr), expr)
    return expr


def attribute_replacements(attr):
    table = {
        "nlargest": ["nsmallest"],
        "nsmallest": ["nlargest"],
        "findall": ["split"],
        "lower": ["upper"],
        "upper": ["lower"],
        "startswith": ["endswith"],
        "endswith": ["startswith"],
    }
    return table.get(attr, [])


def constant_replacements(value):
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, int) and not isinstance(value, bool):
        replacements = []
        for candidate in (value + 1, value - 1, 1 if value == 0 else 0):
            if candidate != value and candidate not in replacements:
                replacements.append(candidate)
        return replacements
    if isinstance(value, float):
        replacements = []
        for candidate in (value + 1.0, value - 1.0):
            if candidate != value and candidate not in replacements:
                replacements.append(candidate)
        return replacements
    if isinstance(value, str):
        return string_replacements(value)
    return []


def string_replacements(value):
    replacements = []
    chars = list(value)
    for index, char in enumerate(chars):
        if not char.isdigit():
            continue
        number = int(char)
        for candidate in (number + 1, number - 1):
            if 0 <= candidate <= 9:
                new_chars = chars[:]
                new_chars[index] = str(candidate)
                mutated = "".join(new_chars)
                if mutated != value and mutated not in replacements:
                    replacements.append(mutated)
        break
    return replacements


def parse_inputs(input_lines):
    parsed = []
    for line in input_lines:
        parsed.append(ast.literal_eval(line))
    return parsed


def plain_function_call(namespace, function_name, args):
    try:
        result = namespace[function_name](*args)
        return {
            "ok": True,
            "result": result,
            "result_text": str(result),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "result": None,
            "result_text": None,
            "error": short_error(exc),
        }


def collect_points(source):
    tree = ast.parse(source)
    collector = MutationPointCollector(collect_risky_names(tree))
    collector.visit(tree)
    return collector.points


def replacement_label(replacement):
    if isinstance(replacement, type) and issubclass(replacement, ast.AST):
        return replacement.__name__
    return repr(replacement)


def candidate_codes(source):
    tree_for_risk = ast.parse(source)
    risky_names = collect_risky_names(tree_for_risk)
    collector = MutationPointCollector(risky_names)
    collector.visit(tree_for_risk)
    points = collector.points
    seen = set()
    for index, point in enumerate(points):
        for replacement in point["replacements"]:
            tree = ast.parse(source)
            replacement_value = replacement
            transformer = ApplyMutation(
                index,
                point["kind"],
                replacement_value if not isinstance(replacement_value, type) else replacement_value,
                risky_names,
            )
            mutated_tree = transformer.visit(tree)
            ast.fix_missing_locations(mutated_tree)
            if not transformer.applied:
                continue
            try:
                code = ast.unparse(mutated_tree) + "\n"
            except Exception:
                continue
            if code in seen or code == source:
                continue
            seen.add(code)
            yield {
                "code": code,
                "mutation": {
                    "point_index": index,
                    "kind": point["kind"],
                    "line": point["line"],
                    "replacement": replacement_label(replacement),
                },
            }


def prepare_original(task_dir, max_events, expected_inputs):
    source_path = task_dir / "code.py"
    input_path = task_dir / "sample_code_inputs.txt"
    input_lines = read_input_lines(input_path)
    if input_lines is None:
        return None, {"status": "missing_inputs", "reason": str(input_path)}
    if expected_inputs > 0 and len(input_lines) != expected_inputs:
        return None, {"status": "wrong_input_count", "input_count": len(input_lines)}
    source = source_path.read_text(encoding="utf-8")
    parsed_inputs = parse_inputs(input_lines)
    function_name = choose_callable_function(source, parsed_inputs, preferred_name=get_test_entry_name(str(task_dir)))
    if not function_name:
        return None, {"status": "missing_function"}

    try:
        namespace = compile_namespace(source, source_path.resolve())
        statement_map = build_statement_line_map(source, function_name)
    except Exception as exc:
        return None, {"status": "original_setup_error", "reason": short_error(exc)}

    plain_runs = []
    for input_index, input_value in enumerate(parsed_inputs, start=1):
        run = plain_function_call(namespace, function_name, call_args(input_value))
        if not run["ok"]:
            return None, {
                "status": "original_runtime_error",
                "input_index": input_index,
                "reason": run["error"],
            }
        plain_runs.append(
            {
                "input_index": input_index,
                "input": input_lines[input_index - 1],
                "value": input_value,
                "output_text": run["result_text"],
                "output": jsonable(run["result"]),
            }
        )

    traced_runs = []
    for plain_run in plain_runs:
        run = trace_function_call(
            namespace,
            source_path.resolve(),
            function_name,
            call_args(plain_run["value"]),
            max_events,
        )
        if not run["ok"]:
            return None, {
                "status": "original_trace_error",
                "input_index": plain_run["input_index"],
                "reason": run["error"],
            }
        traced_runs.append(
            {
                **plain_run,
                "statement_trace": statement_trace(run["trace"], statement_map),
                "relative_trace": relative_trace(run["trace"], min(statement_map) if statement_map else 1),
            }
        )

    return {
        "source": source,
        "function_name": function_name,
        "parsed_inputs": parsed_inputs,
        "input_lines": input_lines,
        "runs": traced_runs,
        "plain_runs": plain_runs,
    }, None


def fast_validate_candidate(task_dir, original, candidate, require_all_changed):
    task_id = task_dir.name
    virtual_path = (task_dir / f"__trace_candidate_{task_id}.py").resolve()
    source = candidate["code"]
    function_name = original["function_name"]

    try:
        namespace = compile_namespace(source, virtual_path)
        if function_name not in namespace:
            return None
    except Exception:
        return None

    changed_count = 0
    detail = []
    for original_run, input_value in zip(original["plain_runs"], original["parsed_inputs"]):
        mutated_run = plain_function_call(namespace, function_name, call_args(input_value))
        if not mutated_run["ok"]:
            return None
        changed = mutated_run["result_text"] != original_run["output_text"]
        if changed:
            changed_count += 1
        detail.append(
            {
                "input_index": original_run["input_index"],
                "input": original_run["input"],
                "original_output_text": original_run["output_text"],
                "mutated_output_text": mutated_run["result_text"],
                "output_changed": changed,
            }
        )

    if require_all_changed:
        if changed_count != len(original["runs"]):
            return None
    elif changed_count < 1:
        return None

    return {
        "namespace": namespace,
        "virtual_path": virtual_path,
        "changed_count": changed_count,
        "total_inputs": len(original["plain_runs"]),
        "mutation": candidate["mutation"],
        "details": detail,
    }


def trace_validate_candidate(original, candidate, fast_result, max_events):
    function_name = original["function_name"]
    statement_map = build_statement_line_map(candidate["code"], function_name)

    for original_run, input_value in zip(original["runs"], original["parsed_inputs"]):
        mutated_run = trace_function_call(
            fast_result["namespace"],
            fast_result["virtual_path"],
            function_name,
            call_args(input_value),
            max_events,
        )
        if not mutated_run["ok"]:
            return None
        mutated_statement_trace = statement_trace(mutated_run["trace"], statement_map)
        if mutated_statement_trace != original_run["statement_trace"]:
            return None

    return {
        "changed_count": fast_result["changed_count"],
        "total_inputs": fast_result["total_inputs"],
        "mutation": fast_result["mutation"],
        "details": fast_result["details"],
    }


def generate_for_task(task_dir, output_dir, max_events, expected_inputs, require_all_changed, max_candidates):
    started = time.perf_counter()
    original, error = prepare_original(task_dir, max_events, expected_inputs)
    if error:
        return {"task_id": task_dir.name, "elapsed_seconds": round(time.perf_counter() - started, 4), **error}

    tried = 0
    fast_passed = 0
    trace_checked = 0
    for candidate in candidate_codes(original["source"]):
        tried += 1
        if max_candidates and tried > max_candidates:
            break
        fast_result = fast_validate_candidate(task_dir, original, candidate, require_all_changed)
        if fast_result is None:
            continue
        fast_passed += 1
        trace_checked += 1
        validation = trace_validate_candidate(original, candidate, fast_result, max_events)
        if validation is None:
            continue
        output_path = output_dir / f"{task_dir.name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(candidate["code"], encoding="utf-8")
        return {
            "task_id": task_dir.name,
            "status": "generated",
            "output_path": str(output_path.resolve()),
            "candidates_tried": tried,
            "fast_passed": fast_passed,
            "trace_checked": trace_checked,
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            **validation,
        }

    return {
        "task_id": task_dir.name,
        "status": "no_candidate",
        "candidates_tried": tried,
        "fast_passed": fast_passed,
        "trace_checked": trace_checked,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "candidate_points": len(collect_points(original["source"])),
    }


def iter_task_dirs(task_root, task=None, tasks=None, limit=None, start_after=None):
    if tasks:
        task_dirs = [task_root / task_id for task_id in tasks]
    elif task:
        task_dirs = [task_root / task]
    else:
        task_dirs = sorted((path for path in task_root.glob("task_*") if path.is_dir()), key=task_sort_key)
    if start_after:
        task_dirs = [path for path in task_dirs if task_sort_key(path) > task_sort_key(start_after)]
    if limit is not None:
        task_dirs = task_dirs[:limit]
    return task_dirs


def summarize(records):
    status_counts = {}
    changed_counts = []
    input_counts = []
    for record in records:
        status = record["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "generated":
            changed_counts.append(record["changed_count"])
            input_counts.append(record["total_inputs"])
    generated_tasks = status_counts.get("generated", 0)
    total_tasks = len(records)
    return {
        "total_tasks": total_tasks,
        "status_counts": status_counts,
        "generated_tasks": generated_tasks,
        "coverage_rate": round(generated_tasks / total_tasks, 4) if total_tasks else 0.0,
        "total_generated_inputs": sum(input_counts),
        "min_changed_count": min(changed_counts) if changed_counts else 0,
        "max_changed_count": max(changed_counts) if changed_counts else 0,
        "avg_changed_count": round(sum(changed_counts) / len(changed_counts), 4) if changed_counts else 0.0,
        "total_elapsed_seconds": round(sum(record.get("elapsed_seconds", 0.0) for record in records), 4),
        "avg_elapsed_seconds": round(
            sum(record.get("elapsed_seconds", 0.0) for record in records) / len(records),
            4,
        )
        if records
        else 0.0,
        "total_candidates_tried": sum(record.get("candidates_tried", 0) for record in records),
        "total_trace_checked": sum(record.get("trace_checked", 0) for record in records),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate local trace-preserving non-equivalent mutations.")
    parser.add_argument("--task_root", default=str(MBPP_DIR))
    parser.add_argument("--output_dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--expected_inputs_per_task", type=int, default=10, help="Use 0 to accept the actual number of inputs in each task.")
    parser.add_argument("--max_events", type=int, default=5000000)
    parser.add_argument("--max_candidates", type=int, default=0, help="0 means no limit")
    parser.add_argument("--require_all_changed", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task")
    parser.add_argument("--tasks", help="Comma-separated task ids, for example task_65,task_84")
    parser.add_argument("--start_after", help="Continue after this task id, for example task_101")
    parser.add_argument("--append_report", action="store_true", help="Append JSONL records instead of overwriting the report.")
    args = parser.parse_args()

    task_root = Path(args.task_root)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)
    summary_path = Path(args.summary)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    report_mode = "a" if args.append_report else "w"
    selected_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()] if args.tasks else None
    with report_path.open(report_mode, encoding="utf-8") as report:
        for task_dir in iter_task_dirs(task_root, args.task, selected_tasks, args.limit, args.start_after):
            record = generate_for_task(
                task_dir,
                output_dir,
                args.max_events,
                args.expected_inputs_per_task,
                args.require_all_changed,
                args.max_candidates,
            )
            records.append(record)
            report.write(json.dumps(record, ensure_ascii=False) + "\n")
            report.flush()
            print(
                f"[{record['status']}] {record['task_id']} "
                f"changed={record.get('changed_count', 0)}/{record.get('total_inputs', args.expected_inputs_per_task)} "
                f"tried={record.get('candidates_tried', 0)}",
                flush=True,
            )

    all_records = []
    if report_path.exists():
        with report_path.open("r", encoding="utf-8") as f:
            all_records = [json.loads(line) for line in f if line.strip()]

    summary = summarize(all_records)
    summary.update(
        {
            "command": " ".join(sys.argv),
            "purpose": (
                "Generate one local AST single-point non-equivalent mutation per task, "
                "requiring all selected inputs to run and preserve the original statement trace."
            ),
            "output_dir": str(output_dir.resolve()),
            "report": str(report_path.resolve()),
        }
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
