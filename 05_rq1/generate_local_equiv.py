import argparse
import ast
import copy
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03_splice"))

from audit_non_equiv_line_trace import call_args, compile_namespace, jsonable, short_error, task_sort_key
from paths import MBPP_DIR, ROOT
from splice_utils import choose_callable_function, get_test_entry_name


DEFAULT_OUTPUT_DIR = ROOT / "equivalent_transform_local"
DEFAULT_REPORT = ROOT / "reports" / "rq1_local_equiv_generation.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "rq1_local_equiv_generation_summary.json"


RULE_PRIORITY = {
    "invert_if_else": 100,
    "mirror_compare": 90,
    "constant_equivalent_expr": 80,
    "double_not_condition": 70,
    "rename_locals": 60,
    "introduce_return_temp": 50,
}


def read_input_lines(path):
    if not path.exists():
        return None
    return [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_inputs(input_lines):
    return [parse_input_line(line) for line in input_lines]


def parse_input_line(line):
    try:
        return ast.literal_eval(line)
    except Exception:
        return eval(line, {"__builtins__": {}}, {"inf": float("inf")})


def plain_function_call(namespace, function_name, args):
    try:
        result = namespace[function_name](*args)
        return {"ok": True, "result": result, "result_text": str(result), "error": None}
    except Exception as exc:
        return {"ok": False, "result": None, "result_text": None, "error": short_error(exc)}


def local_names(function_node):
    names = set(arg.arg for arg in function_node.args.args)
    names.update(arg.arg for arg in function_node.args.posonlyargs)
    names.update(arg.arg for arg in function_node.args.kwonlyargs)
    if function_node.args.vararg:
        names.add(function_node.args.vararg.arg)
    if function_node.args.kwarg:
        names.add(function_node.args.kwarg.arg)
    for node in ast.walk(function_node):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return {
        name
        for name in names
        if not (name.startswith("__") and name.endswith("__"))
        and name not in {"self", "cls"}
        and name != function_node.name
    }


def find_function(tree, function_name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    return None


def ast_size(tree):
    return sum(1 for _ in ast.walk(tree))


class LocalRenamer(ast.NodeTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def visit_arg(self, node):
        if node.arg in self.mapping:
            node.arg = self.mapping[node.arg]
        return node

    def visit_Name(self, node):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node


class ConstantEquivalentRewriter(ast.NodeTransformer):
    def __init__(self, target_index):
        self.target_index = target_index
        self.current_index = -1
        self.applied = False

    def visit_Constant(self, node):
        if not constant_is_rewritable(node.value):
            return node
        self.current_index += 1
        if self.current_index != self.target_index:
            return node
        self.applied = True
        return ast.copy_location(equivalent_constant_expr(node.value), node)


class ReturnTempIntroducer(ast.NodeTransformer):
    def __init__(self, target_index, temp_name):
        self.target_index = target_index
        self.temp_name = temp_name
        self.current_index = -1
        self.applied = False

    def visit_Return(self, node):
        self.generic_visit(node)
        if node.value is None:
            return node
        self.current_index += 1
        if self.current_index != self.target_index:
            return node
        self.applied = True
        assign = ast.Assign(
            targets=[ast.Name(id=self.temp_name, ctx=ast.Store())],
            value=node.value,
        )
        ret = ast.Return(value=ast.Name(id=self.temp_name, ctx=ast.Load()))
        return [ast.copy_location(assign, node), ast.copy_location(ret, node)]


class IfElseInverter(ast.NodeTransformer):
    def __init__(self, target_index):
        self.target_index = target_index
        self.current_index = -1
        self.applied = False

    def visit_If(self, node):
        self.generic_visit(node)
        if not node.orelse:
            return node
        self.current_index += 1
        if self.current_index != self.target_index:
            return node
        self.applied = True
        node.test = ast.copy_location(ast.UnaryOp(op=ast.Not(), operand=node.test), node.test)
        node.body, node.orelse = node.orelse, node.body
        return node


class CompareMirror(ast.NodeTransformer):
    def __init__(self, target_index):
        self.target_index = target_index
        self.current_index = -1
        self.applied = False

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) != 1 or len(node.comparators) != 1:
            return node
        mirrored = mirror_compare_op(node.ops[0])
        if mirrored is None:
            return node
        self.current_index += 1
        if self.current_index != self.target_index:
            return node
        self.applied = True
        return ast.copy_location(
            ast.Compare(left=node.comparators[0], ops=[mirrored], comparators=[node.left]),
            node,
        )


class BoolDoubleNot(ast.NodeTransformer):
    def __init__(self, target_index):
        self.target_index = target_index
        self.current_index = -1
        self.applied = False

    def visit_If(self, node):
        self.generic_visit(node)
        self.current_index += 1
        if self.current_index != self.target_index:
            return node
        self.applied = True
        inner = ast.UnaryOp(op=ast.Not(), operand=node.test)
        node.test = ast.copy_location(ast.UnaryOp(op=ast.Not(), operand=inner), node.test)
        return node


def mirror_compare_op(op):
    table = {
        ast.Lt: ast.Gt,
        ast.LtE: ast.GtE,
        ast.Gt: ast.Lt,
        ast.GtE: ast.LtE,
        ast.Eq: ast.Eq,
        ast.NotEq: ast.NotEq,
        ast.Is: ast.Is,
        ast.IsNot: ast.IsNot,
    }
    op_cls = table.get(type(op))
    return op_cls() if op_cls else None


def constant_is_rewritable(value):
    if isinstance(value, bool):
        return True
    if isinstance(value, int) and not isinstance(value, bool):
        return True
    if isinstance(value, float):
        return True
    if isinstance(value, str):
        return value != ""
    return False


def equivalent_constant_expr(value):
    if isinstance(value, bool):
        return ast.UnaryOp(op=ast.Not(), operand=ast.Constant(value=not value))
    if isinstance(value, int) and not isinstance(value, bool):
        return ast.BinOp(left=ast.Constant(value=value + 1), op=ast.Sub(), right=ast.Constant(value=1))
    if isinstance(value, float):
        return ast.BinOp(left=ast.Constant(value=value + 1.0), op=ast.Sub(), right=ast.Constant(value=1.0))
    if isinstance(value, str):
        return ast.BinOp(left=ast.Constant(value=value), op=ast.Add(), right=ast.Constant(value=""))
    return ast.Constant(value=value)


def count_nodes(function_node, node_type, predicate=None):
    count = 0
    for node in ast.walk(function_node):
        if isinstance(node, node_type) and (predicate is None or predicate(node)):
            count += 1
    return count


def apply_transform(source, transformer):
    tree = ast.parse(source)
    mutated = transformer.visit(tree)
    ast.fix_missing_locations(mutated)
    if not getattr(transformer, "applied", True):
        return None
    try:
        return ast.unparse(mutated) + "\n"
    except Exception:
        return None


def candidate_codes(source, function_name):
    base_tree = ast.parse(source)
    function_node = find_function(base_tree, function_name)
    if function_node is None:
        return

    seen = set()

    names = sorted(local_names(function_node))
    if names:
        mapping = {name: f"{name}_eq" for name in names[: min(8, len(names))]}
        tree = copy.deepcopy(base_tree)
        function_copy = find_function(tree, function_name)
        LocalRenamer(mapping).visit(function_copy)
        ast.fix_missing_locations(tree)
        code = ast.unparse(tree) + "\n"
        if code != source and code not in seen:
            seen.add(code)
            yield {"code": code, "rule": "rename_locals", "score": len(mapping)}

    return_count = count_nodes(function_node, ast.Return, lambda node: node.value is not None)
    existing_names = local_names(function_node)
    for index in range(return_count):
        temp_name = f"__equiv_tmp_{index}"
        while temp_name in existing_names:
            temp_name += "_x"
        code = apply_transform(source, ReturnTempIntroducer(index, temp_name))
        if code and code != source and code not in seen:
            seen.add(code)
            yield {"code": code, "rule": "introduce_return_temp", "score": 5}

    const_count = count_nodes(function_node, ast.Constant, lambda node: constant_is_rewritable(node.value))
    for index in range(min(const_count, 30)):
        code = apply_transform(source, ConstantEquivalentRewriter(index))
        if code and code != source and code not in seen:
            seen.add(code)
            yield {"code": code, "rule": "constant_equivalent_expr", "score": 3}

    if_count = count_nodes(function_node, ast.If, lambda node: bool(node.orelse))
    for index in range(min(if_count, 10)):
        code = apply_transform(source, IfElseInverter(index))
        if code and code != source and code not in seen:
            seen.add(code)
            yield {"code": code, "rule": "invert_if_else", "score": 9}

    compare_count = count_nodes(
        function_node,
        ast.Compare,
        lambda node: len(node.ops) == 1 and len(node.comparators) == 1 and mirror_compare_op(node.ops[0]) is not None,
    )
    for index in range(min(compare_count, 20)):
        code = apply_transform(source, CompareMirror(index))
        if code and code != source and code not in seen:
            seen.add(code)
            yield {"code": code, "rule": "mirror_compare", "score": 4}

    if_total = count_nodes(function_node, ast.If)
    for index in range(min(if_total, 20)):
        code = apply_transform(source, BoolDoubleNot(index))
        if code and code != source and code not in seen:
            seen.add(code)
            yield {"code": code, "rule": "double_not_condition", "score": 4}


def prepare_original(task_dir, input_file):
    source_path = task_dir / "code.py"
    input_path = task_dir / input_file
    if not source_path.exists():
        return None, {"status": "missing_code", "reason": str(source_path)}
    input_lines = read_input_lines(input_path)
    if input_lines is None:
        return None, {"status": "missing_inputs", "reason": str(input_path)}

    source = source_path.read_text(encoding="utf-8")
    try:
        parsed_inputs = parse_inputs(input_lines)
    except Exception as exc:
        return None, {"status": "input_parse_error", "reason": short_error(exc)}

    function_name = choose_callable_function(source, parsed_inputs, preferred_name=get_test_entry_name(str(task_dir)))
    if not function_name:
        return None, {"status": "missing_function"}

    try:
        namespace = compile_namespace(source, source_path.resolve())
    except Exception as exc:
        return None, {"status": "original_setup_error", "reason": short_error(exc)}

    runs = []
    for input_index, input_value in enumerate(parsed_inputs, start=1):
        run = plain_function_call(namespace, function_name, call_args(input_value))
        if not run["ok"]:
            return None, {
                "status": "original_runtime_error",
                "input_index": input_index,
                "reason": run["error"],
            }
        runs.append(
            {
                "input_index": input_index,
                "input": input_lines[input_index - 1],
                "value": input_value,
                "output_text": run["result_text"],
                "output": jsonable(run["result"]),
            }
        )

    return {
        "source": source,
        "function_name": function_name,
        "input_lines": input_lines,
        "parsed_inputs": parsed_inputs,
        "runs": runs,
    }, None


def validate_candidate(task_dir, original, candidate):
    task_id = task_dir.name
    virtual_path = (task_dir / f"__equiv_candidate_{task_id}.py").resolve()
    function_name = original["function_name"]
    try:
        namespace = compile_namespace(candidate["code"], virtual_path)
    except Exception:
        return None
    if function_name not in namespace:
        return None

    details = []
    for original_run, input_value in zip(original["runs"], original["parsed_inputs"]):
        mutated_run = plain_function_call(namespace, function_name, call_args(input_value))
        if not mutated_run["ok"]:
            return None
        same = mutated_run["result_text"] == original_run["output_text"]
        if not same:
            return None
        details.append(
            {
                "input_index": original_run["input_index"],
                "input": original_run["input"],
                "output_text": original_run["output_text"],
            }
        )

    try:
        original_tree = ast.parse(original["source"])
        mutated_tree = ast.parse(candidate["code"])
        edit_proxy = abs(ast_size(mutated_tree) - ast_size(original_tree)) + candidate["score"]
    except Exception:
        edit_proxy = candidate["score"]

    return {
        "rule": candidate["rule"],
        "priority": RULE_PRIORITY.get(candidate["rule"], 0),
        "edit_proxy": edit_proxy,
        "total_inputs": len(original["runs"]),
        "details": details,
    }


def generate_for_task(task_dir, output_dir, input_file, max_candidates):
    started = time.perf_counter()
    original, error = prepare_original(task_dir, input_file)
    if error:
        return {"task_id": task_dir.name, "elapsed_seconds": round(time.perf_counter() - started, 4), **error}

    tried = 0
    valid_candidates = []
    for candidate in candidate_codes(original["source"], original["function_name"]):
        tried += 1
        if max_candidates and tried > max_candidates:
            break
        validation = validate_candidate(task_dir, original, candidate)
        if validation is None:
            continue
        valid_candidates.append({**candidate, **validation})

    if not valid_candidates:
        return {
            "task_id": task_dir.name,
            "status": "no_candidate",
            "candidates_tried": tried,
            "total_inputs": len(original["runs"]),
            "elapsed_seconds": round(time.perf_counter() - started, 4),
        }

    selected = max(valid_candidates, key=lambda item: (item.get("priority", 0), item["edit_proxy"], item["rule"]))
    output_path = output_dir / f"{task_dir.name}.py" if output_dir else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(selected["code"], encoding="utf-8")
    return {
        "task_id": task_dir.name,
        "status": "generated",
        "output_path": str(output_path.resolve()) if output_path is not None else "",
        "rule": selected["rule"],
        "edit_proxy": selected["edit_proxy"],
        "valid_candidates": len(valid_candidates),
        "candidates_tried": tried,
        "total_inputs": selected["total_inputs"],
        "elapsed_seconds": round(time.perf_counter() - started, 4),
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


def summarize(records):
    status_counts = {}
    rule_counts = {}
    generated = []
    for record in records:
        status_counts[record["status"]] = status_counts.get(record["status"], 0) + 1
        if record["status"] == "generated":
            generated.append(record)
            rule = record.get("rule", "")
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
    total = len(records)
    return {
        "total_tasks": total,
        "status_counts": status_counts,
        "generated_tasks": len(generated),
        "coverage_rate": round(len(generated) / total, 4) if total else 0.0,
        "rule_counts": rule_counts,
        "total_validated_inputs": sum(record.get("total_inputs", 0) for record in generated),
        "min_edit_proxy": min((record.get("edit_proxy", 0) for record in generated), default=0),
        "max_edit_proxy": max((record.get("edit_proxy", 0) for record in generated), default=0),
        "avg_edit_proxy": round(
            sum(record.get("edit_proxy", 0) for record in generated) / len(generated),
            4,
        )
        if generated
        else 0.0,
        "total_elapsed_seconds": round(sum(record.get("elapsed_seconds", 0.0) for record in records), 4),
        "avg_elapsed_seconds": round(
            sum(record.get("elapsed_seconds", 0.0) for record in records) / total,
            4,
        )
        if total
        else 0.0,
        "total_candidates_tried": sum(record.get("candidates_tried", 0) for record in records),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate local equivalent mutations and validate on full candidate inputs.")
    parser.add_argument("--task_root", default=str(MBPP_DIR))
    parser.add_argument("--input_file", default="code_inputs.txt")
    parser.add_argument("--output_dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--max_candidates", type=int, default=80, help="0 means no limit")
    parser.add_argument("--no_report", action="store_true", help="Print results only; do not write JSONL/summary files.")
    parser.add_argument("--no_write_code", action="store_true", help="Validate candidates without writing generated code files.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task")
    parser.add_argument("--tasks", help="Comma-separated task ids, for example task_65,task_84")
    args = parser.parse_args()

    task_root = Path(args.task_root)
    output_dir = None if args.no_write_code else Path(args.output_dir)
    report_path = Path(args.report)
    summary_path = Path(args.summary)
    if not args.no_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
    selected_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()] if args.tasks else None

    records = []
    report = None if args.no_report else report_path.open("w", encoding="utf-8")
    try:
        for task_dir in iter_task_dirs(task_root, args.task, selected_tasks, args.limit):
            record = generate_for_task(task_dir, output_dir, args.input_file, args.max_candidates)
            records.append(record)
            if report is not None:
                report.write(json.dumps(record, ensure_ascii=False) + "\n")
                report.flush()
            print(
                f"[{record['status']}] {record['task_id']} "
                f"rule={record.get('rule', '-')} inputs={record.get('total_inputs', 0)} "
                f"tried={record.get('candidates_tried', 0)}",
                flush=True,
            )
    finally:
        if report is not None:
            report.close()

    summary = summarize(records)
    summary.update(
        {
            "command": " ".join(sys.argv),
            "purpose": (
                "Generate local equivalent mutations and validate that all inputs in the selected input file "
                "produce identical outputs to the original code."
            ),
            "output_dir": str(output_dir.resolve()) if output_dir is not None else "",
            "report": "" if args.no_report else str(report_path.resolve()),
            "input_file": args.input_file,
        }
    )
    if not args.no_report:
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
