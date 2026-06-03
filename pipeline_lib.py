# [auto-patched by patch_imports.py]
import sys as _sys
from pathlib import Path as _Path


def _resolve_repo_root(start_path):
    for parent in [start_path] + list(start_path.parents):
        if (parent / "config_loader.py").exists():
            return parent
    cwd = _Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "config_loader.py").exists():
            return parent
    return start_path.parents[2] if len(start_path.parents) >= 2 else start_path


ROOT = _resolve_repo_root(_Path(__file__).resolve())
if str(ROOT) not in _sys.path:
    _sys.path.insert(0, str(ROOT))
MUTATION_DIR = ROOT / "02_mutation"
if str(MUTATION_DIR) not in _sys.path:
    _sys.path.insert(0, str(MUTATION_DIR))

from config_loader import load_config
from mutation_runner import call_llm, extract_result_block, validate_python_code
from paths import MBPP_DIR, EQUIV_TRANSFORM, NON_EQUIV_TRANSFORM

import json
import os
import subprocess
import sys


RUN_CODE = ROOT / "04_local_exec" / "exec_main.py"


def read_lines(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def list_task_ids(transform_root, limit=None):
    if not os.path.exists(transform_root):
        return []
    task_ids = []
    for fname in os.listdir(transform_root):
        if fname.startswith("task_") and fname.endswith(".py"):
            task_ids.append(fname[:-3])
    task_ids = sorted(task_ids)
    if limit is not None:
        task_ids = task_ids[:limit]
    return task_ids


def write_report(report, report_path):
    report_path = _Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def load_report(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_diff_details(original_lines, mutated_lines, input_lines, max_examples):
    max_len = max(len(original_lines), len(mutated_lines), len(input_lines))
    diffs = []

    for index in range(max_len):
        original = original_lines[index] if index < len(original_lines) else None
        mutated = mutated_lines[index] if index < len(mutated_lines) else None
        if original != mutated:
            input_line = input_lines[index] if index < len(input_lines) else None
            diffs.append(
                {
                    "line": index + 1,
                    "input": input_line,
                    "original": original,
                    "mutated": mutated,
                }
            )
            if len(diffs) >= max_examples:
                break

    return diffs


def build_match_examples(original_lines, input_lines, max_examples):
    examples = []
    max_len = max(len(original_lines), len(input_lines))

    for index in range(max_len):
        original = original_lines[index] if index < len(original_lines) else None
        input_line = input_lines[index] if index < len(input_lines) else None
        examples.append(
            {
                "line": index + 1,
                "input": input_line,
                "output": original,
            }
        )
        if len(examples) >= max_examples:
            break

    return examples


def validate_equivalent(task_ids, max_examples):
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "missing": 0,
        "failures": [],
    }

    for task_id in task_ids:
        results["total"] += 1
        task_dir = os.path.join(str(MBPP_DIR), task_id)
        original_path = os.path.join(task_dir, "sample_code_results.txt")
        equiv_path = os.path.join(task_dir, "sample_code_results_equivalent.txt")
        input_path = os.path.join(task_dir, "sample_code_inputs.txt")

        original_lines = read_lines(original_path)
        equiv_lines = read_lines(equiv_path)
        input_lines = read_lines(input_path) or []

        if original_lines is None or equiv_lines is None:
            results["missing"] += 1
            results["failed"] += 1
            results["failures"].append(
                {
                    "task_id": task_id,
                    "reason": "missing_result",
                    "original_path": original_path if original_lines is None else "",
                    "equiv_path": equiv_path if equiv_lines is None else "",
                }
            )
            continue

        if original_lines == equiv_lines:
            results["passed"] += 1
            continue

        diffs = build_diff_details(original_lines, equiv_lines, input_lines, max_examples)
        results["failed"] += 1
        results["failures"].append(
            {
                "task_id": task_id,
                "reason": "results_differ",
                "original_len": len(original_lines),
                "equiv_len": len(equiv_lines),
                "examples": diffs,
            }
        )

    return results


def validate_non_equivalent(task_ids, max_examples):
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "missing": 0,
        "failures": [],
    }

    for task_id in task_ids:
        results["total"] += 1
        task_dir = os.path.join(str(MBPP_DIR), task_id)
        original_path = os.path.join(task_dir, "sample_code_results.txt")
        mutated_path = os.path.join(task_dir, "sample_code_results_non_equivalent.txt")
        input_path = os.path.join(task_dir, "sample_code_inputs.txt")

        original_lines = read_lines(original_path)
        mutated_lines = read_lines(mutated_path)
        input_lines = read_lines(input_path) or []

        if original_lines is None or mutated_lines is None:
            results["missing"] += 1
            results["failed"] += 1
            results["failures"].append(
                {
                    "task_id": task_id,
                    "reason": "missing_result",
                    "original_path": original_path if original_lines is None else "",
                    "mutated_path": mutated_path if mutated_lines is None else "",
                }
            )
            continue

        if original_lines != mutated_lines:
            results["passed"] += 1
            continue

        results["failed"] += 1
        results["failures"].append(
            {
                "task_id": task_id,
                "reason": "no_difference",
                "total_lines": len(original_lines),
                "examples": build_match_examples(original_lines, input_lines, max_examples),
            }
        )

    return results


def print_summary(label, results):
    print(f"\n===== {label} Detailed Validation =====")
    print(f"Total: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Missing: {results['missing']}")
    if results.get("failures"):
        failing_ids = [item["task_id"] for item in results["failures"]]
        print(f"Failing task ids: {', '.join(failing_ids)}")


def validate_mutations(report_path=None, limit=None, max_examples=3, mode="all"):
    report = {}

    if mode in ("all", "equivalent"):
        eq_task_ids = list_task_ids(str(EQUIV_TRANSFORM), limit)
        eq_results = validate_equivalent(eq_task_ids, max_examples)
        report["equivalent"] = eq_results
        print_summary("Equivalent", eq_results)

    if mode in ("all", "non_equivalent"):
        ne_task_ids = list_task_ids(str(NON_EQUIV_TRANSFORM), limit)
        ne_results = validate_non_equivalent(ne_task_ids, max_examples)
        report["non_equivalent"] = ne_results
        print_summary("Non-Equivalent", ne_results)

    if report_path:
        write_report(report, report_path)
        print(f"\nReport written: {report_path}")

    return report


def build_equivalent_prompt(code_content, failure, max_examples):
    examples = failure.get("examples", [])[:max_examples]
    examples_text = "\n".join(
        [
            f"- input: {ex.get('input')}\n  expected: {ex.get('original')}\n  previous_mutated: {ex.get('mutated')}"
            for ex in examples
        ]
    )

    return f"""
Below is the Python code:
{code_content}

The previous equivalent mutation failed because its outputs differed from the original on the following input/output examples:
{examples_text if examples_text else '- (no examples available)'}

Task: regenerate a semantically equivalent version that preserves 100% functional equivalence.
Requirements:
- Preserve all I/O behavior for all inputs; do not change the algorithm.
- Do not introduce exceptions or type changes.
- Keep changes minimal; apply at most 2 simple transformations (rename variables, reorder independent statements, or add dead code with no side effects).
- Avoid API substitutions or logic changes.
- Return only valid Python code.

Output ONLY the transformed code, wrapped exactly as:
<result>
<your_transformed_code_here>
</result>
"""


def build_non_equivalent_prompt(code_content, failure, max_examples):
    examples = failure.get("examples", [])[:max_examples]
    examples_text = "\n".join(
        [
            f"- input: {ex.get('input')}\n  original_output: {ex.get('output')}"
            for ex in examples
        ]
    )

    return f"""
Below is the Python code:
{code_content}

The previous non-equivalent mutation failed because its outputs were identical to the original on these inputs:
{examples_text if examples_text else '- (no examples available)'}

Task: introduce a single, subtle logical change so that at least one of the above inputs produces a different output.
Requirements:
- Change exactly one operator or literal.
- Keep the rest of the code as close to the original as possible.
- Return only valid Python code.

Output ONLY the transformed code, wrapped exactly as:
<result>
<your_transformed_code_here>
</result>
"""


def iter_failures(report, mode, include_missing):
    section = report.get(mode, {})
    failures = section.get("failures", [])
    if include_missing:
        return failures
    return [item for item in failures if item.get("reason") != "missing_result"]


def resolve_api_config(mode):
    config = load_config()
    model_name = config.get("model_name", "gpt-5.1")
    api_key = config["api_key_fields"][mode]
    base_url = config.get("yunwu_base_url") or config.get("api_base_url")

    if not api_key:
        raise ValueError(f"Missing API key for mode: {mode}")
    if not base_url:
        raise ValueError("Missing base URL. Set yunwu_base_url or api_base_url in config1.json.")

    return model_name, api_key, base_url


def read_code(task_dir):
    code_path = os.path.join(task_dir, "code.py")
    if not os.path.exists(code_path):
        return None
    with open(code_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_with_feedback(task_id, prompt, output_dir, model_name, api_key, base_url, max_attempts, overwrite):
    save_path = os.path.join(output_dir, f"{task_id}.py")
    if os.path.exists(save_path) and not overwrite:
        return "skipped", "output_exists"

    last_error = ""
    for _ in range(max_attempts):
        llm_output = call_llm(prompt, task_id, api_key, base_url, model_name)
        final_code = extract_result_block(llm_output)
        is_valid, error = validate_python_code(final_code)
        if is_valid:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(final_code)
            return "written", ""
        last_error = error

    return "invalid", last_error


def retry_with_feedback(report, mode, limit=None, max_examples=3, max_attempts=3, overwrite=False, include_missing=False):
    model_name, api_key, base_url = resolve_api_config(mode)
    output_dir = str(EQUIV_TRANSFORM) if mode == "equivalent" else str(NON_EQUIV_TRANSFORM)

    failures = iter_failures(report, mode, include_missing)
    if limit is not None:
        failures = failures[:limit]

    summary = {
        "total": len(failures),
        "written": 0,
        "skipped": 0,
        "invalid": 0,
        "missing_code": 0,
        "errors": [],
    }

    for failure in failures:
        task_id = failure.get("task_id")
        task_dir = os.path.join(str(MBPP_DIR), task_id)
        code_content = read_code(task_dir)
        if code_content is None:
            summary["missing_code"] += 1
            summary["errors"].append({"task_id": task_id, "reason": "missing_code"})
            continue

        if mode == "equivalent":
            prompt = build_equivalent_prompt(code_content, failure, max_examples)
        else:
            prompt = build_non_equivalent_prompt(code_content, failure, max_examples)

        status, message = generate_with_feedback(
            task_id,
            prompt,
            output_dir,
            model_name,
            api_key,
            base_url,
            max_attempts,
            overwrite,
        )

        if status == "written":
            summary["written"] += 1
            print(f"[written] {task_id}")
        elif status == "skipped":
            summary["skipped"] += 1
            print(f"[skipped] {task_id}: {message}")
        else:
            summary["invalid"] += 1
            summary["errors"].append({"task_id": task_id, "reason": message})
            print(f"[invalid] {task_id}: {message}")

    print(f"\n===== {mode} Feedback Retry Summary =====")
    print(f"Total: {summary['total']}")
    print(f"Written: {summary['written']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Invalid: {summary['invalid']}")
    print(f"Missing code: {summary['missing_code']}")

    return summary


def run_script(args, label, stop_on_error):
    print(f"\n>>> {label}")
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"[warn] {label} exited with code {result.returncode}")
        if stop_on_error:
            sys.exit(result.returncode)
    return result.returncode


def add_arg(args, flag, value):
    if value is None:
        return args
    return args + [flag, str(value)]


def run_local_exec(mode, timeout, limit, stop_on_error):
    args = [sys.executable, str(RUN_CODE), "--mode", mode]
    args = add_arg(args, "--timeout", timeout)
    args = add_arg(args, "--limit", limit)
    return run_script(args, f"Local exec: {mode}", stop_on_error)


def print_report_summary(title, report):
    if report is None:
        print(f"\n{title}: no report found")
        return

    print(f"\n===== {title} =====")
    for mode in ("equivalent", "non_equivalent"):
        section = report.get(mode)
        if not section:
            continue
        print(
            f"{mode}: total={section.get('total')}, passed={section.get('passed')}, failed={section.get('failed')}, missing={section.get('missing')}"
        )


def run_pipeline(
    limit=None,
    timeout=30,
    max_examples=3,
    max_attempts=3,
    report_dir="reports",
    overwrite=False,
    include_missing=False,
    skip_exec=False,
    skip_retry=False,
    skip_revalidate=False,
    skip_original=False,
    stop_on_error=False,
):
    report_dir = _Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "mutation_failures.json"
    report_path_after = report_dir / "mutation_failures_after_retry.json"

    if not skip_exec:
        if not skip_original:
            run_local_exec("original", timeout, limit, stop_on_error)
        run_local_exec("equivalent", timeout, limit, stop_on_error)
        run_local_exec("non_equivalent", timeout, limit, stop_on_error)

    report = validate_mutations(report_path, limit, max_examples)

    if not skip_retry:
        retry_with_feedback(
            report,
            "equivalent",
            limit,
            max_examples,
            max_attempts,
            overwrite,
            include_missing,
        )
        retry_with_feedback(
            report,
            "non_equivalent",
            limit,
            max_examples,
            max_attempts,
            overwrite,
            include_missing,
        )

        if not skip_exec:
            run_local_exec("equivalent", timeout, limit, stop_on_error)
            run_local_exec("non_equivalent", timeout, limit, stop_on_error)

    if not skip_revalidate:
        report_after = validate_mutations(report_path_after, limit, max_examples)
        print_report_summary("Final report", report_after)
        return report_after

    print_report_summary("Initial report", report)
    return report
