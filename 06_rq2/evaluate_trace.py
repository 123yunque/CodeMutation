import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import (
    LLM_TRACE_EQUIV,
    LLM_TRACE_NON_EQUIV,
    LLM_TRACE_ORIGINAL,
    LOCAL_EQUIV,
    LOCAL_NON_EQUIV,
    LOCAL_ORIGINAL,
)


DIR_PAIRS = {
    "Equivalent Correct": (LLM_TRACE_EQUIV / "correct", LOCAL_EQUIV / "correct"),
    "Equivalent Error": (LLM_TRACE_EQUIV / "error", LOCAL_EQUIV / "error"),
    "Non-Equivalent Correct": (LLM_TRACE_NON_EQUIV / "correct", LOCAL_NON_EQUIV / "correct"),
    "Non-Equivalent Error": (LLM_TRACE_NON_EQUIV / "error", LOCAL_NON_EQUIV / "error"),
    "Original Correct": (LLM_TRACE_ORIGINAL / "correct", LOCAL_ORIGINAL / "correct"),
    "Original Error": (LLM_TRACE_ORIGINAL / "error", LOCAL_ORIGINAL / "error"),
}


def parse_file_to_dict(filepath):
    data = {}
    if not os.path.exists(filepath):
        return data

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            var_name, var_value = line.split(":", 1)
            data[var_name.strip().strip("'").strip('"')] = var_value.strip()
    return data


def task_files(directory):
    if not directory.exists():
        return set()
    return {path.name for path in directory.glob("task_*.txt") if path.is_file()}


def compare_directories(llm_dir, local_dir):
    llm_files = task_files(llm_dir)
    local_files = task_files(local_dir)
    common_files = sorted(llm_files & local_files)

    stats = {
        "llm_exists": llm_dir.exists(),
        "local_exists": local_dir.exists(),
        "llm_files": len(llm_files),
        "local_files": len(local_files),
        "common_files": len(common_files),
        "valid_files": 0,
        "skipped_no_result": 0,
        "result_matches": 0,
        "all_matches": 0,
        "vars_matched": 0,
        "vars_compared": 0,
        "all_match_files": [],
        "result_only_match_files": [],
        "no_result_files": [],
    }

    for fname in common_files:
        llm_dict = parse_file_to_dict(llm_dir / fname)
        local_dict = parse_file_to_dict(local_dir / fname)

        if "result" not in llm_dict or "result" not in local_dict:
            stats["skipped_no_result"] += 1
            stats["no_result_files"].append(fname)
            continue

        stats["valid_files"] += 1
        result_match = llm_dict["result"] == local_dict["result"]
        if result_match:
            stats["result_matches"] += 1

        base_dict, compare_dict = (
            (llm_dict, local_dict) if len(llm_dict) <= len(local_dict) else (local_dict, llm_dict)
        )
        matched = sum(
            1 for var_name, var_value in base_dict.items()
            if var_name in compare_dict and compare_dict[var_name] == var_value
        )
        stats["vars_compared"] += len(base_dict)
        stats["vars_matched"] += matched

        if base_dict and matched == len(base_dict):
            stats["all_matches"] += 1
            stats["all_match_files"].append(fname)
        elif result_match:
            stats["result_only_match_files"].append(fname)

    return stats


def pct(count, total):
    return "n/a" if total == 0 else f"{count / total:.1%}"


def print_file_list(label, files, max_items=30):
    if not files:
        return
    shown = files[:max_items]
    suffix = "" if len(files) <= max_items else f" ... (+{len(files) - max_items} more)"
    print(f"  {label}: {', '.join(shown)}{suffix}")


def main():
    print("Starting RQ2 trace comparison.\n")

    total = {
        "valid_files": 0,
        "skipped_no_result": 0,
        "result_matches": 0,
        "all_matches": 0,
        "vars_matched": 0,
        "vars_compared": 0,
    }

    for label, (llm_dir, local_dir) in DIR_PAIRS.items():
        stats = compare_directories(llm_dir, local_dir)

        print(f"===== {label} =====")
        print(f"LLM dir:   {llm_dir} ({'exists' if stats['llm_exists'] else 'missing'}, files={stats['llm_files']})")
        print(f"Local dir: {local_dir} ({'exists' if stats['local_exists'] else 'missing'}, files={stats['local_files']})")
        print(f"Common task files: {stats['common_files']}")
        print(f"Skipped without result: {stats['skipped_no_result']}")
        print(f"Valid compared files: {stats['valid_files']}")

        if stats["valid_files"]:
            print(f"Result matches: {stats['result_matches']} ({pct(stats['result_matches'], stats['valid_files'])})")
            print(f"All-variable matches: {stats['all_matches']} ({pct(stats['all_matches'], stats['valid_files'])})")
            print(f"Variable match ratio: {stats['vars_matched']} / {stats['vars_compared']} ({pct(stats['vars_matched'], stats['vars_compared'])})")
            print_file_list("All-variable match files", stats["all_match_files"])
            print_file_list("Result-only match files", stats["result_only_match_files"])
        else:
            print_file_list("Files skipped because result is missing", stats["no_result_files"])
        print()

        for key in total:
            total[key] += stats[key]

    print("===== Overall =====")
    print(f"Valid compared files: {total['valid_files']}")
    print(f"Skipped without result: {total['skipped_no_result']}")
    if total["valid_files"]:
        print(f"Result matches: {total['result_matches']} ({pct(total['result_matches'], total['valid_files'])})")
        print(f"All-variable matches: {total['all_matches']} ({pct(total['all_matches'], total['valid_files'])})")
        print(f"Variable match ratio: {total['vars_matched']} / {total['vars_compared']} ({pct(total['vars_matched'], total['vars_compared'])})")


if __name__ == "__main__":
    main()
