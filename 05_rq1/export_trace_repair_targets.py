import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


REPAIR_CATEGORIES = {"invalid_original_runtime_error", "missing_input_slot"}


def main():
    parser = argparse.ArgumentParser(description="Export RQ1 trace audit cases that need local repair.")
    parser.add_argument("--source", required=True, help="Compact classification JSONL")
    parser.add_argument("--output", required=True, help="Repair target JSON")
    args = parser.parse_args()

    targets = []
    by_task = defaultdict(list)
    counts = Counter()
    with Path(args.source).open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("category") not in REPAIR_CATEGORIES:
                continue
            item = {
                "case_id": row.get("case_id"),
                "task_id": row.get("task_id"),
                "input_index": row.get("input_index"),
                "category": row.get("category"),
                "input": row.get("input"),
                "original_error": row.get("original_error"),
            }
            targets.append(item)
            by_task[item["task_id"]].append(item)
            counts[item["category"]] += 1

    report = {
        "source": str(Path(args.source).resolve()),
        "total_repair_cases": len(targets),
        "category_counts": dict(counts),
        "task_counts": {task_id: len(items) for task_id, items in sorted(by_task.items())},
        "targets": targets,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
