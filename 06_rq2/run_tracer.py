import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis_tracer import trace_variables
from paths import (
    LOCAL_EQUIV,
    LOCAL_NON_EQUIV,
    LOCAL_ORIGINAL,
    MBPP_DIR,
)


TRACE_CONFIGS = {
    "original": {
        "root": LOCAL_ORIGINAL,
        "script_prefix": "original",
    },
    "equivalent": {
        "root": LOCAL_EQUIV,
        "script_prefix": "equivalent",
    },
    "non_equivalent": {
        "root": LOCAL_NON_EQUIV,
        "script_prefix": "non_equivalent",
    },
}


def format_result(var_sequences):
    return "\n".join(f"'{var}': {vals}" for var, vals in var_sequences.items())


def iter_task_dirs(limit=None, task=None):
    if task:
        task_dirs = [Path(MBPP_DIR) / task]
    else:
        task_dirs = sorted(path for path in Path(MBPP_DIR).glob("task_*") if path.is_dir())
    if limit is not None:
        task_dirs = task_dirs[:limit]
    return task_dirs


def run_route(mode, status, overwrite=False, limit=None, task=None):
    config = TRACE_CONFIGS[mode]
    target_file = f"sample_{config['script_prefix']}_{status}.py"
    output_dir = Path(config["root"]) / status
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"success": 0, "missing": 0, "skipped": 0, "failed": 0, "without_result": 0}
    print(f"Tracing mode={mode}, status={status}, script={target_file}, output={output_dir}")

    for task_dir in iter_task_dirs(limit, task):
        if not task_dir.is_dir():
            stats["missing"] += 1
            print(f"[missing-task] {task_dir.name}")
            continue

        source_path = task_dir / target_file
        output_path = output_dir / f"{task_dir.name}.txt"

        if not source_path.exists():
            stats["missing"] += 1
            print(f"[missing] {task_dir.name}: {target_file}")
            continue
        if output_path.exists() and not overwrite:
            stats["skipped"] += 1
            print(f"[skip] {task_dir.name}: {output_path.name}")
            continue

        try:
            var_sequences = trace_variables(str(source_path.resolve()))
        except Exception as exc:
            stats["failed"] += 1
            print(f"[failed] {task_dir.name}: {exc}")
            continue

        output_path.write_text(format_result(var_sequences), encoding="utf-8")
        stats["success"] += 1
        if "result" not in var_sequences:
            stats["without_result"] += 1
            print(f"[written-no-result] {task_dir.name}: {output_path.name}")
        else:
            print(f"[written] {task_dir.name}: {output_path.name} ({len(var_sequences)} vars)")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate local RQ2 variable traces.")
    parser.add_argument("--mode", choices=("all",) + tuple(TRACE_CONFIGS), default="all")
    parser.add_argument("--status", choices=("all", "correct", "error"), default="all")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--task", help="Optional task folder name, for example task_100")
    args = parser.parse_args()

    modes = tuple(TRACE_CONFIGS) if args.mode == "all" else (args.mode,)
    statuses = ("correct", "error") if args.status == "all" else (args.status,)

    for mode in modes:
        for status in statuses:
            stats = run_route(mode, status, overwrite=args.overwrite, limit=args.limit, task=args.task)
            print(
                f"Done {mode}/{status}. success={stats['success']}, "
                f"missing={stats['missing']}, skipped={stats['skipped']}, "
                f"failed={stats['failed']}, without_result={stats['without_result']}"
            )


if __name__ == "__main__":
    main()
