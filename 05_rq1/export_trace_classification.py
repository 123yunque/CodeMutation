import argparse
import csv
import json
from pathlib import Path


CATEGORY_BY_STATUS = {
    "pass": "valid_trace_preserving_non_equiv",
    "same_output": "invalid_same_output",
    "statement_trace_diff": "invalid_statement_trace_diff",
    "original_runtime_error": "invalid_original_runtime_error",
    "mutated_runtime_error": "invalid_mutated_runtime_error",
    "function_name_changed": "invalid_function_name_changed",
    "missing_input_slot": "missing_input_slot",
    "input_parse_error": "invalid_input_parse_error",
    "setup_error": "invalid_setup_error",
    "missing_inputs": "missing_inputs",
    "missing_original_code": "missing_original_code",
    "missing_mutated_code": "missing_mutated_code",
}


FIELDS = [
    "case_id",
    "task_id",
    "input_index",
    "category",
    "status",
    "input",
    "original_output_text",
    "mutated_output_text",
    "output_changed",
    "same_statement_trace",
    "same_line_trace",
    "same_relative_trace",
    "original_error",
    "mutated_error",
    "llm_answer",
    "llm_classification",
]


def classify(row):
    status = row.get("status")
    category = CATEGORY_BY_STATUS.get(status, status or "unknown")
    return {
        "case_id": f"{row.get('task_id')}#{row.get('input_index')}",
        "task_id": row.get("task_id"),
        "input_index": row.get("input_index"),
        "category": category,
        "status": status,
        "input": row.get("input"),
        "original_output_text": row.get("original_output_text"),
        "mutated_output_text": row.get("mutated_output_text"),
        "output_changed": row.get("output_changed"),
        "same_statement_trace": row.get("same_statement_trace"),
        "same_line_trace": row.get("same_line_trace"),
        "same_relative_trace": row.get("same_relative_trace"),
        "original_error": row.get("original_error"),
        "mutated_error": row.get("mutated_error"),
        "llm_answer": row.get("llm_answer"),
        "llm_classification": row.get("llm_classification"),
    }


def csv_safe(row):
    safe = {}
    for key, value in row.items():
        if isinstance(value, str):
            safe[key] = value.replace("\r", "\\r").replace("\n", "\\n")
        else:
            safe[key] = value
    return safe


def main():
    parser = argparse.ArgumentParser(description="Export compact per-input RQ1 trace classifications.")
    parser.add_argument("--source", required=True, help="Source audit JSONL")
    parser.add_argument("--jsonl", required=True, help="Output compact classification JSONL")
    parser.add_argument("--csv", required=True, help="Output compact classification CSV")
    parser.add_argument("--summary", required=True, help="Output classification summary JSON")
    args = parser.parse_args()

    source = Path(args.source)
    jsonl_path = Path(args.jsonl)
    csv_path = Path(args.csv)
    summary_path = Path(args.summary)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    counts = {}
    llm_counts = {}
    with source.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            classified = classify(json.loads(line))
            rows.append(classified)
            category = classified["category"]
            counts[category] = counts.get(category, 0) + 1
            llm_class = classified.get("llm_classification")
            if llm_class:
                llm_counts[llm_class] = llm_counts.get(llm_class, 0) + 1

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(csv_safe(row) for row in rows)

    summary = {
        "source": str(source.resolve()),
        "jsonl_report": str(jsonl_path.resolve()),
        "csv_report": str(csv_path.resolve()),
        "total_cases": len(rows),
        "category_counts": counts,
        "llm_classification_counts": llm_counts,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
