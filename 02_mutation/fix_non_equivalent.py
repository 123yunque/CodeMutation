r"""
Repair non-equivalent mutations with local validation.

Examples:
  python 02_mutation\fix_non_equivalent.py --dry_run
  python 02_mutation\fix_non_equivalent.py --task_ids task_3 task_101 --max_attempts 3
  python 02_mutation\fix_non_equivalent.py --max_attempts 3 --llm_output_name gpt51_final
"""

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "02_mutation"))
sys.path.insert(0, str(ROOT / "04_local_exec"))

from config_loader import load_config
from exec_utils import INVALID_LOCAL_RESULT, build_compare_results, run_task
from mutation_runner import call_llm, extract_result_block, validate_python_code
from paths import LLM_NON_EQUIV, MBPP_DIR, NON_EQUIV_TRANSFORM


def load_splice_utils():
    module_path = ROOT / "03_splice" / "splice_utils.py"
    spec = importlib.util.spec_from_file_location("rq1_splice_utils", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load splice utils from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_splice_utils = load_splice_utils()
choose_callable_function = _splice_utils.choose_callable_function
parse_input_lines = _splice_utils.parse_input_lines
write_mutation_task = _splice_utils.write_mutation_task


SCRIPT_OUTPUT = "sample_inputs_non_equivalent.py"
RESULT_FILE = "sample_code_results_non_equivalent.txt"
COMPARE_FILE = "sample_code_compare_results.txt"


def task_sort_key(task_id):
    try:
        return int(task_id.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return task_id


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_lines(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def read_input_literals(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def normalize_task_ids(raw_values):
    task_ids = []
    for value in raw_values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                task_ids.append(item if item.startswith("task_") else f"task_{item}")
    return sorted(set(task_ids), key=task_sort_key)


def discover_problem_tasks(task_root=MBPP_DIR):
    task_root = Path(task_root)
    failed_or_timeout = []
    empty_compare = []
    fully_same = []

    for task_dir in sorted(task_root.glob("task_*"), key=lambda p: task_sort_key(p.name)):
        mutated_path = task_dir / RESULT_FILE
        compare_path = task_dir / COMPARE_FILE

        if not mutated_path.exists():
            failed_or_timeout.append(task_dir.name)
            continue

        if not compare_path.exists() or compare_path.stat().st_size == 0:
            empty_compare.append(task_dir.name)
            continue

        compare_lines = read_lines(compare_path) or []
        if compare_lines and all(line == INVALID_LOCAL_RESULT for line in compare_lines):
            fully_same.append(task_dir.name)

    return {
        "failed_or_timeout": failed_or_timeout,
        "empty_compare": empty_compare,
        "fully_same": fully_same,
    }


def build_repair_prompt(task_id, original_code, current_mutation, inputs, original_outputs, reason):
    return f"""
Below is the original Python solution for {task_id}:
{original_code}

The previous non-equivalent mutation failed local validation.
Failure type: {reason}

Previous mutation:
{current_mutation}

Sample inputs:
{json.dumps(inputs, ensure_ascii=False, indent=2)}

Original outputs for those inputs:
{json.dumps(original_outputs, ensure_ascii=False, indent=2)}

Generate a corrected NON-EQUIVALENT mutation.

Requirements:
- Return a complete valid Python module.
- Keep the same public function behavior shape: same callable entry point or a callable with the same input arity.
- The code must execute successfully for every sample input above.
- At least one listed sample input must produce an output different from the original outputs above.
- Inspect the listed sample inputs and original outputs before choosing the mutation. If every original output is False, None, an empty list, or otherwise identical, mutate an early guard, predicate, regex, threshold, return expression, or loop boundary so one listed sample definitely differs without raising an exception.
- If all original outputs are False, changing one failing validation branch from returning False to returning True is allowed when it makes at least one listed sample differ.
- Prefer one small logical mutation: comparison, boolean connector, arithmetic operator, constant, regex pattern, index expression, or return expression.
- Do not add input(), file I/O, network calls, sleeps, randomness, comments, Markdown, or explanations.
- Do not merely repeat the previous mutation if it did not change any listed output.

Output ONLY the transformed code, wrapped exactly as:
<result>
<your_transformed_code_here>
</result>
"""


def run_candidate(task_id, code_text, inputs, original_outputs, timeout):
    is_valid, error = validate_python_code(code_text)
    if not is_valid:
        return {
            "ok": False,
            "reason": f"syntax: {error}",
            "outputs": [],
            "diff_indices": [],
        }

    func_name = choose_callable_function(code_text, inputs)
    if not func_name:
        return {"ok": False, "reason": "no callable function", "outputs": [], "diff_indices": []}

    validation_dir = ROOT / ".tmp_non_equiv_validation"
    validation_dir.mkdir(exist_ok=True)
    script_path = validation_dir / f"{task_id}_{int(time.time() * 1000)}.py"
    runner = (
        code_text
        + "\n\n"
        + f"inputs = {repr(inputs)}\n"
        + "result = []\n"
        + "for inp in inputs:\n"
        + f"    result.append({func_name}(*inp))\n"
        + "for item in result:\n"
        + "    print(str(item))\n"
    )

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(runner)
        env = os.environ.copy()
        env.setdefault("PYTHONHASHSEED", "0")
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "timeout", "outputs": [], "diff_indices": []}
    finally:
        try:
            script_path.unlink()
        except OSError:
            pass

    if completed.returncode != 0:
        stderr = completed.stderr.strip().splitlines()
        reason = stderr[-1] if stderr else f"exit={completed.returncode}"
        return {"ok": False, "reason": f"runtime: {reason}", "outputs": [], "diff_indices": []}

    outputs = completed.stdout.splitlines()
    if len(outputs) != len(original_outputs):
        return {
            "ok": False,
            "reason": f"output count mismatch: {len(outputs)} != {len(original_outputs)}",
            "outputs": outputs,
            "diff_indices": [],
        }

    diff_indices = [idx for idx, (got, exp) in enumerate(zip(outputs, original_outputs)) if got != exp]
    if not diff_indices:
        return {"ok": False, "reason": "no differing sample output", "outputs": outputs, "diff_indices": []}

    return {"ok": True, "reason": "", "outputs": outputs, "diff_indices": diff_indices}


def refresh_task_outputs(task_id, timeout):
    task_dir = Path(MBPP_DIR) / task_id
    transform_path = Path(NON_EQUIV_TRANSFORM) / f"{task_id}.py"

    splice_status = write_mutation_task(str(task_dir), str(transform_path), SCRIPT_OUTPUT, RESULT_FILE)
    if splice_status != "written":
        return False, f"splice {splice_status}"

    try:
        result = run_task(str(task_dir), SCRIPT_OUTPUT, timeout, output_files=(RESULT_FILE,))
    except subprocess.TimeoutExpired:
        return False, "spliced script timeout"
    if result["status"] != "success":
        return False, f"spliced script failed: {result.get('stderr', '')}"

    original_lines = read_lines(task_dir / "sample_code_results.txt")
    mutated_lines = read_lines(task_dir / RESULT_FILE)
    if original_lines is None or mutated_lines is None:
        return False, "missing local result after refresh"

    compare_results, _ = build_compare_results(original_lines, mutated_lines)
    with open(task_dir / COMPARE_FILE, "w", encoding="utf-8") as f:
        for line in compare_results:
            f.write(line + "\n")
    return True, ""


def delete_stale_llm_output(task_id, output_name):
    if not output_name:
        return None
    output_path = Path(LLM_NON_EQUIV) / output_name / f"{task_id}.txt"
    if output_path.exists():
        output_path.unlink()
        return str(output_path)
    return None


def repair_one_task(task_id, args, api_key, base_url, model_name):
    task_dir = Path(MBPP_DIR) / task_id
    transform_path = Path(NON_EQUIV_TRANSFORM) / f"{task_id}.py"
    code_path = task_dir / "code.py"
    input_path = task_dir / "sample_code_inputs.txt"
    original_result_path = task_dir / "sample_code_results.txt"

    if not task_dir.exists():
        return {"task_id": task_id, "status": "missing_task"}
    if not code_path.exists():
        return {"task_id": task_id, "status": "missing_code"}
    if not input_path.exists():
        return {"task_id": task_id, "status": "missing_inputs"}
    if not original_result_path.exists():
        return {"task_id": task_id, "status": "missing_original_results"}

    inputs = parse_input_lines(str(input_path))
    input_literals = read_input_literals(input_path)
    original_outputs = read_lines(original_result_path) or []
    if not inputs or len(inputs) != len(original_outputs):
        return {
            "task_id": task_id,
            "status": "invalid_local_baseline",
            "input_count": len(inputs),
            "original_output_count": len(original_outputs),
        }

    original_code = read_text(code_path)
    current_mutation = read_text(transform_path) if transform_path.exists() else ""
    old_hash = hashlib.sha256(current_mutation.encode("utf-8")).hexdigest() if current_mutation else None

    reason = "auto-discovered problem"
    if not (task_dir / RESULT_FILE).exists():
        reason = "execution failed or timed out"
    elif not (task_dir / COMPARE_FILE).exists() or (task_dir / COMPARE_FILE).stat().st_size == 0:
        reason = "empty compare"
    else:
        compare_lines = read_lines(task_dir / COMPARE_FILE) or []
        if compare_lines and all(line == INVALID_LOCAL_RESULT for line in compare_lines):
            reason = "no sample input triggers a difference"

    attempts = []
    for attempt in range(1, args.max_attempts + 1):
        prompt = build_repair_prompt(task_id, original_code, current_mutation, input_literals, original_outputs, reason)
        llm_output = call_llm(prompt, task_id, api_key, base_url, model_name, max_retries=args.api_retries)
        candidate = extract_result_block(llm_output)
        validation = run_candidate(task_id, candidate, inputs, original_outputs, args.timeout)
        attempts.append(
            {
                "attempt": attempt,
                "ok": validation["ok"],
                "reason": validation["reason"],
                "diff_indices": validation["diff_indices"],
            }
        )
        if not validation["ok"]:
            print(f"[retry] {task_id} attempt={attempt}: {validation['reason']}")
            current_mutation = candidate
            reason = validation["reason"]
            continue

        with open(transform_path, "w", encoding="utf-8") as f:
            f.write(candidate.rstrip() + "\n")

        refreshed, refresh_error = refresh_task_outputs(task_id, args.timeout)
        if not refreshed:
            return {
                "task_id": task_id,
                "status": "refresh_failed",
                "attempts": attempts,
                "error": refresh_error,
                "old_hash": old_hash,
            }

        deleted_llm_output = delete_stale_llm_output(task_id, args.llm_output_name)
        return {
            "task_id": task_id,
            "status": "fixed",
            "attempts": attempts,
            "diff_count": len(validation["diff_indices"]),
            "diff_indices": validation["diff_indices"],
            "old_hash": old_hash,
            "new_hash": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
            "deleted_llm_output": deleted_llm_output,
        }

    return {"task_id": task_id, "status": "unfixed", "attempts": attempts, "old_hash": old_hash}


def refresh_one_existing_task(task_id, args):
    task_dir = Path(MBPP_DIR) / task_id
    transform_path = Path(NON_EQUIV_TRANSFORM) / f"{task_id}.py"
    input_path = task_dir / "sample_code_inputs.txt"
    original_result_path = task_dir / "sample_code_results.txt"

    if not task_dir.exists():
        return {"task_id": task_id, "status": "missing_task"}
    if not transform_path.exists():
        return {"task_id": task_id, "status": "missing_transform"}
    if not input_path.exists():
        return {"task_id": task_id, "status": "missing_inputs"}
    if not original_result_path.exists():
        return {"task_id": task_id, "status": "missing_original_results"}

    inputs = parse_input_lines(str(input_path))
    original_outputs = read_lines(original_result_path) or []
    code_text = read_text(transform_path)
    validation = run_candidate(task_id, code_text, inputs, original_outputs, args.timeout)
    if not validation["ok"]:
        return {
            "task_id": task_id,
            "status": "validation_failed",
            "reason": validation["reason"],
        }

    refreshed, refresh_error = refresh_task_outputs(task_id, args.timeout)
    if not refreshed:
        return {
            "task_id": task_id,
            "status": "refresh_failed",
            "reason": refresh_error,
            "diff_indices": validation["diff_indices"],
        }

    deleted_llm_output = delete_stale_llm_output(task_id, args.llm_output_name)
    return {
        "task_id": task_id,
        "status": "refreshed",
        "diff_count": len(validation["diff_indices"]),
        "diff_indices": validation["diff_indices"],
        "deleted_llm_output": deleted_llm_output,
    }


def main():
    parser = argparse.ArgumentParser(description="Repair non-equivalent mutations that fail local validation.")
    parser.add_argument("--task_ids", nargs="*", help="Optional task ids, e.g. task_3 task_101 or 3,101")
    parser.add_argument("--max_attempts", type=int, default=3, help="LLM candidates per task")
    parser.add_argument("--api_retries", type=int, default=2, help="Retries for each LLM call")
    parser.add_argument("--timeout", type=int, default=30, help="Validation timeout per candidate")
    parser.add_argument("--model_name", help="Override model name from config1.json")
    parser.add_argument("--limit", type=int, help="Limit discovered task count")
    parser.add_argument("--dry_run", action="store_true", help="Only list tasks that would be repaired")
    parser.add_argument(
        "--refresh_only",
        action="store_true",
        help="Validate existing transforms and refresh local outputs without calling the API",
    )
    parser.add_argument(
        "--llm_output_name",
        help="Delete stale non-equivalent RQ1 LLM outputs under this output directory for fixed tasks",
    )
    parser.add_argument("--report", default="reports/non_equivalent_fix_report.json", help="JSON report path")
    args = parser.parse_args()

    discovered = discover_problem_tasks()
    task_ids = normalize_task_ids(args.task_ids)
    if not task_ids:
        task_ids = sorted(
            set(discovered["failed_or_timeout"] + discovered["empty_compare"] + discovered["fully_same"]),
            key=task_sort_key,
        )
    if args.limit is not None:
        task_ids = task_ids[: args.limit]

    print("Problem summary:")
    print(f"  failed_or_timeout: {len(discovered['failed_or_timeout'])}")
    print(f"  empty_compare: {len(discovered['empty_compare'])}")
    print(f"  fully_same: {len(discovered['fully_same'])}")
    print(f"  selected: {len(task_ids)}")
    for task_id in task_ids:
        print(f"  - {task_id}")

    if args.dry_run:
        return

    if args.refresh_only:
        report = {
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "refresh_only",
            "selected_task_count": len(task_ids),
            "discovered": discovered,
            "results": [],
        }
        for index, task_id in enumerate(task_ids, start=1):
            print(f"[refresh] {index}/{len(task_ids)} {task_id}")
            result = refresh_one_existing_task(task_id, args)
            report["results"].append(result)
            print(f"[{result['status']}] {task_id}")

            report_path = ROOT / args.report
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(ROOT / args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        refreshed_count = sum(1 for item in report["results"] if item["status"] == "refreshed")
        print(f"Done. refreshed={refreshed_count}/{len(task_ids)} report={ROOT / args.report}")
        return

    config = load_config()
    api_key = config["api_key_fields"]["non_equivalent"]
    base_url = config.get("yunwu_base_url") or config.get("api_base_url")
    model_name = args.model_name or config.get("model_name", "gpt-5.1")
    if not api_key:
        raise ValueError("Missing non_equivalent API key.")
    if not base_url:
        raise ValueError("Missing base URL. Set yunwu_base_url or api_base_url in config1.json.")

    report = {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_name": model_name,
        "selected_task_count": len(task_ids),
        "discovered": discovered,
        "results": [],
    }

    for index, task_id in enumerate(task_ids, start=1):
        print(f"[repair] {index}/{len(task_ids)} {task_id}")
        result = repair_one_task(task_id, args, api_key, base_url, model_name)
        report["results"].append(result)
        print(f"[{result['status']}] {task_id}")

        report_path = ROOT / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ROOT / args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    fixed_count = sum(1 for item in report["results"] if item["status"] == "fixed")
    print(f"Done. fixed={fixed_count}/{len(task_ids)} report={ROOT / args.report}")


if __name__ == "__main__":
    main()
