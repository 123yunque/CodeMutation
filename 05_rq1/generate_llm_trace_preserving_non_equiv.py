import argparse
import ast
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02_mutation"))

from config_loader import load_config
from generate_trace_preserving_non_equiv import (
    fast_validate_candidate,
    iter_task_dirs,
    prepare_original,
    trace_validate_candidate,
)
from mutation_runner import call_llm, extract_result_block, validate_python_code
from paths import MBPP_DIR, ROOT


DEFAULT_OUTPUT_DIR = ROOT / "non_equivalent_transform_llm_trace_preserving"
DEFAULT_REPORT = ROOT / "reports" / "rq1_llm_trace_preserving_non_equiv_generation.jsonl"
DEFAULT_SUMMARY = ROOT / "reports" / "rq1_llm_trace_preserving_non_equiv_generation_summary.json"


def numbered_code(source):
    return "\n".join(f"{index:04d}: {line}" for index, line in enumerate(source.splitlines(), start=1))


def compact_trace_cases(original):
    cases = []
    for run in original["runs"]:
        cases.append(
            {
                "input_index": run["input_index"],
                "input": run["input"],
                "original_output": run["output_text"],
                "statement_trace": run["statement_trace"],
            }
        )
    return cases


def build_prompt(task_id, original, require_all_changed):
    change_requirement = (
        "Ensure every listed input produces a different output from its original_output."
        if require_all_changed
        else "Ensure the original correct solution becomes incorrect for at least one listed input."
    )
    trace_json = json.dumps(compact_trace_cases(original), ensure_ascii=False, indent=2)
    return f"""
Below is the Python code:
```python
{original["source"]}
```

Below are the sampled inputs, original outputs, and original executed statement traces for this task.
The statement trace uses AST statement positions such as body.0:Assign or body.1:If.body.0:Return.
```json
{trace_json}
```

You are a Mutation Testing Engineer. Introduce a single, subtle logical change that alters the correct answer of the problem while preserving the original executed statement trace.

Mutation Rules (pick exactly ONE):
1. Relational Operator Replacement (ROR): Flip or relax a comparison, such as > to <, < to <=, or == to !=.
2. Logical Connector Replacement (LCR): Swap a logical connector, such as and to or.
3. Arithmetic Operator Replacement (AOR): Change an arithmetic operator, such as + to - or * to +.
4. Constant Value Mutation (CVM): Change a critical threshold or constant by a minimal margin.
5. Expression Result Mutation (ERM): Change one returned or assigned expression without changing control flow.

Requirements:
- Change exactly one expression-level token, operator, or literal.
- Keep the rest of the code as close to the original as possible.
- Keep the target function name and signature unchanged.
- For every listed input, the mutated code must execute the exact same statement_trace in the exact same order as the original.
- The mutated code must run successfully on every listed input.
- {change_requirement}
- Prefer changing outputs for as many listed inputs as possible.
- Do not add, delete, reorder, or reindent control-flow statements.
- Do not add or remove if/for/while/return/try/with statements.
- Do not add imports, helper functions, print/input/file I/O, randomness, comments, or exception handling.
- Return only valid Python code.

Output ONLY the transformed code, wrapped exactly as:
<result>
<your_transformed_code_here>
</result>
""".strip()


def validate_llm_code(task_dir, original, code_text, max_events, require_all_changed):
    is_valid, error = validate_python_code(code_text)
    if not is_valid:
        return None, {"status": "invalid_python", "reason": error}

    candidate = {"code": code_text, "mutation": {"source": "llm"}}
    fast_result = fast_validate_candidate(task_dir, original, candidate, require_all_changed)
    if fast_result is None:
        return None, {"status": "failed_output_check"}

    trace_result = trace_validate_candidate(original, candidate, fast_result, max_events)
    if trace_result is None:
        return None, {"status": "failed_statement_trace_check"}

    return trace_result, None


def generate_one(task_dir, output_dir, model_name, api_key, base_url, max_events, expected_inputs, max_attempts, require_all_changed, save_prompt_dir):
    started = time.perf_counter()
    original, error = prepare_original(task_dir, max_events, expected_inputs)
    if error:
        return {"task_id": task_dir.name, "elapsed_seconds": round(time.perf_counter() - started, 4), **error}

    prompt = build_prompt(task_dir.name, original, require_all_changed)
    if save_prompt_dir:
        prompt_path = Path(save_prompt_dir) / f"{task_dir.name}.prompt.txt"
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
    else:
        prompt_path = None

    attempts = []
    for attempt in range(1, max_attempts + 1):
        raw = call_llm(prompt, task_dir.name, api_key, base_url, model_name, max_retries=1)
        code_text = extract_result_block(raw)
        validation, validation_error = validate_llm_code(
            task_dir,
            original,
            code_text,
            max_events,
            require_all_changed,
        )
        attempts.append(
            {
                "attempt": attempt,
                "status": "valid" if validation else validation_error["status"],
                "reason": None if validation else validation_error.get("reason"),
                "code": code_text,
            }
        )
        if not validation:
            continue

        output_path = output_dir / f"{task_dir.name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code_text, encoding="utf-8")
        return {
            "task_id": task_dir.name,
            "status": "generated",
            "output_path": str(output_path.resolve()),
            "prompt_path": str(prompt_path.resolve()) if prompt_path else None,
            "attempts": attempts,
            "changed_count": validation["changed_count"],
            "total_inputs": validation["total_inputs"],
            "details": validation["details"],
            "original_trace_cases": compact_trace_cases(original),
            "elapsed_seconds": round(time.perf_counter() - started, 4),
        }

    return {
        "task_id": task_dir.name,
        "status": "failed",
        "prompt_path": str(prompt_path.resolve()) if prompt_path else None,
        "attempts": attempts,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
    }


def summarize(records):
    counts = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    generated = [record for record in records if record["status"] == "generated"]
    return {
        "total_tasks": len(records),
        "status_counts": counts,
        "generated_tasks": len(generated),
        "total_changed_inputs": sum(record.get("changed_count", 0) for record in generated),
        "total_inputs_in_generated_tasks": sum(record.get("total_inputs", 0) for record in generated),
        "avg_changed_count": round(sum(record.get("changed_count", 0) for record in generated) / len(generated), 4)
        if generated
        else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate LLM trace-preserving non-equivalent mutations.")
    parser.add_argument("--task_root", default=str(MBPP_DIR))
    parser.add_argument("--output_dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--prompt_dir", default=str(ROOT / "reports" / "llm_trace_preserving_prompts"))
    parser.add_argument("--model_name")
    parser.add_argument("--max_events", type=int, default=5000000)
    parser.add_argument("--expected_inputs_per_task", type=int, default=10)
    parser.add_argument("--max_attempts", type=int, default=2)
    parser.add_argument("--require_all_changed", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task")
    parser.add_argument("--tasks", help="Comma-separated task ids")
    args = parser.parse_args()

    config = load_config()
    model_name = args.model_name or config.get("model_name", "gpt-5.1")
    api_key = config["api_key_fields"]["non_equivalent"]
    base_url = config.get("yunwu_base_url") or config.get("api_base_url")
    if not api_key:
        raise ValueError("Missing non_equivalent API key")
    if not base_url:
        raise ValueError("Missing API base URL")

    task_root = Path(args.task_root)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)
    summary_path = Path(args.summary)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    selected_tasks = [item.strip() for item in args.tasks.split(",") if item.strip()] if args.tasks else None
    records = []
    with report_path.open("w", encoding="utf-8") as report:
        for task_dir in iter_task_dirs(task_root, task=args.task, tasks=selected_tasks, limit=args.limit):
            record = generate_one(
                task_dir,
                output_dir,
                model_name,
                api_key,
                base_url,
                args.max_events,
                args.expected_inputs_per_task,
                args.max_attempts,
                args.require_all_changed,
                args.prompt_dir,
            )
            records.append(record)
            report.write(json.dumps(record, ensure_ascii=False) + "\n")
            report.flush()
            print(
                f"[{record['status']}] {record['task_id']} "
                f"changed={record.get('changed_count', 0)}/{record.get('total_inputs', args.expected_inputs_per_task)}",
                flush=True,
            )

    summary = summarize(records)
    summary.update(
        {
            "command": " ".join(sys.argv),
            "purpose": (
                "Small-scale LLM generation of non-equivalent mutations using original outputs and "
                "original statement traces in the prompt, followed by local statement-trace validation."
            ),
            "output_dir": str(output_dir.resolve()),
            "report": str(report_path.resolve()),
            "prompt_dir": str(Path(args.prompt_dir).resolve()),
        }
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
