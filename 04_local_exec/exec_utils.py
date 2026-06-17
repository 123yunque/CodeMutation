import os
import re
import subprocess

from paths import MBPP_DIR, NON_EQUIV_TRANSFORM
from rq1_config import get_mode_config


INVALID_LOCAL_RESULT = "变异前后结果相同，认为该测试用例无效"


def task_sort_key(name):
    match = re.search(r"(\d+)$", name)
    return int(match.group(1)) if match else name


def iter_task_dirs(base_dir):
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    return sorted(folders, key=task_sort_key)


def run_task(task_dir, script_name, timeout):
    script_path = os.path.join(task_dir, script_name)
    if not os.path.exists(script_path):
        return {
            "status": "missing",
            "returncode": None,
            "stderr": f"Missing script: {script_path}",
        }

    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    result = subprocess.run(
        ["python", script_name],
        cwd=task_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    return {
        "status": "success" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stderr": result.stderr.strip(),
    }


def run_mode(mode, timeout=30, limit=None, base_dir=MBPP_DIR):
    base_dir = str(base_dir)
    if not os.path.exists(base_dir):
        print(f"Missing task directory: {base_dir}")
        return None

    mode_config = get_mode_config(mode)
    script_name = mode_config["input_script"]
    folders = iter_task_dirs(base_dir)
    if limit is not None:
        folders = folders[:limit]

    summary = {"total": len(folders), "success": 0, "failed": 0, "missing": 0, "timeout": 0}
    print(f"Running mode={mode}, script={script_name}, tasks={len(folders)}")

    for folder in folders:
        task_dir = os.path.join(base_dir, folder)
        try:
            result = run_task(task_dir, script_name, timeout)
        except subprocess.TimeoutExpired:
            summary["timeout"] += 1
            print(f"[timeout] {folder}")
            continue

        status = result["status"]
        summary[status] += 1
        if status == "success":
            print(f"[done] {folder}")
        elif status == "missing":
            print(f"[missing] {folder}: {result['stderr']}")
        else:
            print(f"[failed] {folder}: exit={result['returncode']}")
            if result["stderr"]:
                print(result["stderr"])

    return summary


def print_exec_summary(mode, summary):
    print("\n===== Local Execution Summary =====")
    print(f"Mode: {mode}")
    print(f"Total: {summary['total']}")
    print(f"Success: {summary['success']}")
    print(f"Failed: {summary['failed']}")
    print(f"Missing: {summary['missing']}")
    print(f"Timeout: {summary['timeout']}")


def read_lines(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def build_compare_results(original_lines, mutated_lines):
    compare_results = []
    same_count = 0
    max_len = max(len(original_lines), len(mutated_lines))

    for index in range(max_len):
        original = original_lines[index] if index < len(original_lines) else ""
        mutated = mutated_lines[index] if index < len(mutated_lines) else ""
        if original == mutated:
            compare_results.append(INVALID_LOCAL_RESULT)
            same_count += 1
        else:
            compare_results.append(mutated)
    return compare_results, same_count


def compare_non_equivalent_results(task_root=MBPP_DIR, transform_root=NON_EQUIV_TRANSFORM):
    task_root = str(task_root)
    transform_root = str(transform_root)
    results = []

    for fname in sorted(os.listdir(transform_root)):
        if not fname.startswith("task_") or not fname.endswith(".py"):
            continue

        task_id = fname[:-3]
        task_dir = os.path.join(task_root, task_id)
        original_path = os.path.join(task_dir, "sample_code_results.txt")
        mutated_path = os.path.join(task_dir, "sample_code_results_non_equivalent.txt")
        compare_path = os.path.join(task_dir, "sample_code_compare_results.txt")

        original_lines = read_lines(original_path)
        mutated_lines = read_lines(mutated_path)
        if original_lines is None or mutated_lines is None:
            missing = []
            if original_lines is None:
                missing.append(original_path)
            if mutated_lines is None:
                missing.append(mutated_path)
            print(f"[missing] {task_id}: {', '.join(missing)}")
            continue

        compare_results, same_count = build_compare_results(original_lines, mutated_lines)
        with open(compare_path, "w", encoding="utf-8") as f:
            for line in compare_results:
                f.write(line + "\n")
        results.append((task_id, same_count, len(compare_results)))

    return results


def print_compare_summary(results):
    total_same = sum(item[1] for item in results)
    total_cases = sum(item[2] for item in results)
    fully_same = sum(1 for _, same_count, total in results if same_count == total and total > 0)

    print("\n===== Non-Equivalent Compare Summary =====")
    print(f"Tasks: {len(results)}")
    print(f"Invalid same-result cases: {total_same} / {total_cases}")
    print(f"Fully same tasks: {fully_same}")
    if total_cases:
        print(f"Invalid-case ratio: {total_same / total_cases:.2%}")
