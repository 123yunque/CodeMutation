import argparse
import ast as pyast
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import ROOT


LLM_DIRS = {
    "Original Correct": ROOT / "block_original_llm" / "correct",
    "Original Error": ROOT / "block_original_llm" / "error",
    "Equivalent Correct": ROOT / "block_equivalent_llm" / "correct",
    "Equivalent Error": ROOT / "block_equivalent_llm" / "error",
    "Non-Equivalent Correct": ROOT / "block_non_equivalent_llm" / "correct",
    "Non-Equivalent Error": ROOT / "block_non_equivalent_llm" / "error",
}

LOCAL_DIRS = {
    "Original Correct": ROOT / "block_original_local" / "correct",
    "Original Error": ROOT / "block_original_local" / "error",
    "Equivalent Correct": ROOT / "block_equivalent_local" / "correct",
    "Equivalent Error": ROOT / "block_equivalent_local" / "error",
    "Non-Equivalent Correct": ROOT / "block_non_equivalent_local" / "correct",
    "Non-Equivalent Error": ROOT / "block_non_equivalent_local" / "error",
}


def parse_sequence_file(filepath: Path) -> dict:
    result = {}
    if not filepath.exists():
        return result

    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue

        key_part, value_part = line.split(":", 1)
        key = key_part.strip().strip("'\"")
        value_text = value_part.strip()
        try:
            result[key] = pyast.literal_eval(value_text)
        except Exception:
            try:
                result[key] = pyast.literal_eval(_normalize_block_list(value_text))
            except Exception:
                result[key] = []
    return result


def _normalize_block_list(value: str) -> str:
    value = value.replace('"', "'")
    return re.sub(r"\b(B\d+)\b(?!['])", r"'\1'", value)


def normalize_sequence(seq: list) -> list[str]:
    return [str(item) for item in seq] if seq else []


def edit_distance(seq1: list, seq2: list) -> int:
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def block_similarity(gt_seq: list, llm_seq: list) -> float:
    if not gt_seq and not llm_seq:
        return 1.0
    max_len = max(len(gt_seq), len(llm_seq))
    return round(1 - edit_distance(gt_seq, llm_seq) / max_len, 4)


def value_accuracy(gt_vals: list, llm_vals: list) -> float:
    if not gt_vals:
        return 1.0 if not llm_vals else 0.0
    matches = sum(
        1
        for index, value in enumerate(gt_vals)
        if index < len(llm_vals) and value == llm_vals[index]
    )
    return round(matches / len(gt_vals), 4)


def classify_error(gt_blocks: list, llm_blocks: list, gt_vals: list, llm_vals: list) -> str:
    if gt_blocks == llm_blocks:
        if gt_vals == llm_vals:
            return "PERFECT"
        return "PATH_OK_VALUE_ERR"

    gt_set = set(gt_blocks)
    llm_set = set(llm_blocks)
    if gt_set == llm_set:
        if len(gt_blocks) != len(llm_blocks):
            return "WRONG_ITER_COUNT"
        return "WRONG_ORDER"
    if llm_set - gt_set:
        return "WRONG_BRANCH"
    if len(llm_blocks) < len(gt_blocks):
        return "EARLY_TERMINATION"
    return "MIXED_ERROR"


def compare_one_file(gt_path: Path, llm_path: Path) -> dict:
    gt_data = parse_sequence_file(gt_path)
    llm_data = parse_sequence_file(llm_path)

    gt_blocks = normalize_sequence(gt_data.get("block_sequence", []))
    llm_blocks = normalize_sequence(llm_data.get("block_sequence", []))

    output_var = next((key for key in gt_data if key != "block_sequence"), "result")
    gt_vals = normalize_sequence(gt_data.get(output_var, []))
    llm_vals = normalize_sequence(llm_data.get(output_var, []))

    block_exact = gt_blocks == llm_blocks
    value_exact = gt_vals == llm_vals
    final_gt = gt_vals[-1] if gt_vals else None
    final_llm = llm_vals[-1] if llm_vals else None
    final_correct = final_gt == final_llm and final_gt is not None

    return {
        "block_exact_match": block_exact,
        "block_similarity": block_similarity(gt_blocks, llm_blocks),
        "value_exact_match": value_exact,
        "value_accuracy": value_accuracy(gt_vals, llm_vals),
        "final_output_correct": final_correct,
        "reasoning_illusion": final_correct and not block_exact,
        "error_type": classify_error(gt_blocks, llm_blocks, gt_vals, llm_vals),
        "gt_block_len": len(gt_blocks),
        "llm_block_len": len(llm_blocks),
    }


def task_files(directory: Path) -> set[str]:
    if not directory.exists():
        return set()
    return {path.name for path in directory.glob("task_*.txt") if path.is_file()}


def compare_directories(llm_dir: Path, local_dir: Path) -> dict:
    common = sorted(task_files(llm_dir) & task_files(local_dir))
    if not common:
        return {}

    per_file = {
        filename: compare_one_file(local_dir / filename, llm_dir / filename)
        for filename in common
    }
    total = len(per_file)
    error_dist = {}
    for metrics in per_file.values():
        error_type = metrics["error_type"]
        error_dist[error_type] = error_dist.get(error_type, 0) + 1

    return {
        "total": total,
        "block_exact_count": sum(m["block_exact_match"] for m in per_file.values()),
        "avg_block_similarity": round(
            sum(m["block_similarity"] for m in per_file.values()) / total,
            4,
        ),
        "value_exact_count": sum(m["value_exact_match"] for m in per_file.values()),
        "avg_value_accuracy": round(
            sum(m["value_accuracy"] for m in per_file.values()) / total,
            4,
        ),
        "final_correct_count": sum(m["final_output_correct"] for m in per_file.values()),
        "illusion_count": sum(m["reasoning_illusion"] for m in per_file.values()),
        "error_distribution": error_dist,
        "per_file": per_file,
    }


def print_stats(label: str, stats: dict) -> None:
    if not stats:
        print(f"=== {label} ===")
        print("No comparable files or directory missing.\n")
        return

    total = stats["total"]
    print(f"=== {label} ===")
    print(f"Valid compared files: {total}")
    print(f"Block exact match: {stats['block_exact_count']} ({stats['block_exact_count'] / total:.1%})")
    print(f"Average block similarity: {stats['avg_block_similarity']:.4f}")
    print(f"Value exact match: {stats['value_exact_count']} ({stats['value_exact_count'] / total:.1%})")
    print(f"Average value accuracy: {stats['avg_value_accuracy']:.4f}")
    print(f"Final output correct: {stats['final_correct_count']} ({stats['final_correct_count'] / total:.1%})")
    print(f"Reasoning illusion: {stats['illusion_count']} ({stats['illusion_count'] / total:.1%})")
    print("Error distribution:")
    for error_type, count in sorted(stats["error_distribution"].items(), key=lambda item: -item[1]):
        print(f"  {error_type:<25} {count:>4} ({count / total:.1%})")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RQ2 CFG block traces.")
    parser.add_argument("--label", choices=("all",) + tuple(LLM_DIRS), default="all")
    args = parser.parse_args()

    labels = LLM_DIRS if args.label == "all" else {args.label: LLM_DIRS[args.label]}

    global_total = 0
    global_block_exact = 0
    global_value_exact = 0
    global_final_correct = 0
    global_illusion = 0
    global_block_similarity = 0.0
    global_value_accuracy = 0.0
    global_error_dist = {}

    for label in labels:
        stats = compare_directories(LLM_DIRS[label], LOCAL_DIRS[label])
        print_stats(label, stats)
        if not stats:
            continue

        total = stats["total"]
        global_total += total
        global_block_exact += stats["block_exact_count"]
        global_value_exact += stats["value_exact_count"]
        global_final_correct += stats["final_correct_count"]
        global_illusion += stats["illusion_count"]
        global_block_similarity += stats["avg_block_similarity"] * total
        global_value_accuracy += stats["avg_value_accuracy"] * total
        for error_type, count in stats["error_distribution"].items():
            global_error_dist[error_type] = global_error_dist.get(error_type, 0) + count

    if global_total:
        print("=== Overall ===")
        print(f"Total valid files: {global_total}")
        print(f"Block exact match rate: {global_block_exact / global_total:.1%}")
        print(f"Average block similarity: {global_block_similarity / global_total:.4f}")
        print(f"Value exact match rate: {global_value_exact / global_total:.1%}")
        print(f"Average value accuracy: {global_value_accuracy / global_total:.4f}")
        print(f"Final output correct rate: {global_final_correct / global_total:.1%}")
        print(f"Reasoning illusion rate: {global_illusion / global_total:.1%}")
        print("Global error distribution:")
        for error_type, count in sorted(global_error_dist.items(), key=lambda item: -item[1]):
            print(f"  {error_type:<25} {count:>5} ({count / global_total:.1%})")


if __name__ == "__main__":
    main()
