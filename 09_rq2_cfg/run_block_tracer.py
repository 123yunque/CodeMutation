import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from block_tracer import detect_output_var, format_trace_result, trace_block_and_output
from cfg_builder import blocks_to_dict, build_cfg
from paths import MBPP_DIR, ROOT


FILE_CONFIG = {
    "sample_original_correct.py": ROOT / "block_original_local" / "correct",
    "sample_original_error.py": ROOT / "block_original_local" / "error",
    "sample_equivalent_correct.py": ROOT / "block_equivalent_local" / "correct",
    "sample_equivalent_error.py": ROOT / "block_equivalent_local" / "error",
    "sample_non_equivalent_correct.py": ROOT / "block_non_equivalent_local" / "correct",
    "sample_non_equivalent_error.py": ROOT / "block_non_equivalent_local" / "error",
}


def iter_task_dirs(task: str | None = None, limit: int | None = None):
    if task:
        task_dirs = [Path(MBPP_DIR) / task]
    else:
        task_dirs = sorted(path for path in Path(MBPP_DIR).glob("task_*") if path.is_dir())
    if limit is not None:
        task_dirs = task_dirs[:limit]
    return task_dirs


def process_one(task_dir: Path, target_file: str, output_dir: Path, overwrite: bool) -> str:
    source_path = task_dir / target_file
    save_txt = output_dir / f"{task_dir.name}.txt"
    save_cfg = output_dir / f"{task_dir.name}_cfg.json"
    label = f"{task_dir.name}/{target_file}"

    if not source_path.exists():
        return f"[missing] {label}"
    if save_txt.exists() and not overwrite:
        return f"[skip] {label}"

    source_code = source_path.read_text(encoding="utf-8")
    output_var = detect_output_var(source_code)

    try:
        block_seq, val_seq, _ = trace_block_and_output(
            str(source_path.resolve()),
            output_var=output_var,
        )
    except Exception as exc:
        block_seq, val_seq = [], [f"ERROR: {exc}"]

    output_dir.mkdir(parents=True, exist_ok=True)
    save_txt.write_text(
        format_trace_result(block_seq, val_seq, output_var),
        encoding="utf-8",
    )

    try:
        _, blocks = build_cfg(source_code)
        save_cfg.write_text(
            json.dumps(
                {"output_var": output_var, "blocks": blocks_to_dict(blocks)},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        save_cfg.write_text(
            json.dumps({"output_var": output_var, "blocks": {}, "error": str(exc)}),
            encoding="utf-8",
        )

    return f"[written] {label}: blocks={len(block_seq)}, values={len(val_seq)}"


def selected_files(mode: str, status: str):
    modes = ("original", "equivalent", "non_equivalent") if mode == "all" else (mode,)
    statuses = ("correct", "error") if status == "all" else (status,)
    for selected_mode in modes:
        for selected_status in statuses:
            target_file = f"sample_{selected_mode}_{selected_status}.py"
            yield target_file, FILE_CONFIG[target_file]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local RQ2 CFG block traces.")
    parser.add_argument("--mode", choices=("all", "original", "equivalent", "non_equivalent"), default="all")
    parser.add_argument("--status", choices=("all", "correct", "error"), default="all")
    parser.add_argument("--task", help="Optional task folder name, for example task_100")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    task_dirs = iter_task_dirs(task=args.task, limit=args.limit)
    print(f"Found {len(task_dirs)} task folders.")

    for target_file, output_dir in selected_files(args.mode, args.status):
        print(f"\n=== {target_file} -> {output_dir} ===")
        stats = {"written": 0, "missing": 0, "skip": 0}
        for task_dir in task_dirs:
            result = process_one(task_dir, target_file, output_dir, args.overwrite)
            print(result)
            if result.startswith("[written]"):
                stats["written"] += 1
            elif result.startswith("[missing]"):
                stats["missing"] += 1
            elif result.startswith("[skip]"):
                stats["skip"] += 1
        print(f"Done. written={stats['written']}, missing={stats['missing']}, skipped={stats['skip']}")


if __name__ == "__main__":
    main()
