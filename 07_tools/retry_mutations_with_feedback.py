# Compatibility wrapper. The implementation lives in 02_mutation/pipeline/pipeline_lib.py.
import sys as _sys
from pathlib import Path as _Path


ROOT = _Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT / "02_mutation" / "pipeline"
if str(PIPELINE_DIR) not in _sys.path:
    _sys.path.insert(0, str(PIPELINE_DIR))

import argparse

from pipeline_lib import load_report, retry_with_feedback


def main():
    parser = argparse.ArgumentParser(description="Regenerate failed mutations with feedback examples.")
    parser.add_argument("--report", required=True, help="JSON report from validate_mutations_detailed")
    parser.add_argument(
        "--mode",
        default="all",
        choices=("all", "equivalent", "non_equivalent"),
        help="Which mutation type to retry",
    )
    parser.add_argument("--limit", type=int, help="Optional limit on number of failures")
    parser.add_argument("--max_examples", type=int, default=3, help="Max failure examples included in the prompt")
    parser.add_argument("--max_attempts", type=int, default=3, help="Max regeneration attempts per task")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--include_missing", action="store_true", help="Include failures that have missing results")
    args = parser.parse_args()

    report = load_report(args.report)
    if report is None:
        raise FileNotFoundError(args.report)

    if args.mode in ("all", "equivalent"):
        retry_with_feedback(
            report,
            "equivalent",
            args.limit,
            args.max_examples,
            args.max_attempts,
            args.overwrite,
            args.include_missing,
        )

    if args.mode in ("all", "non_equivalent"):
        retry_with_feedback(
            report,
            "non_equivalent",
            args.limit,
            args.max_examples,
            args.max_attempts,
            args.overwrite,
            args.include_missing,
        )


if __name__ == "__main__":
    main()
