# Compatibility wrapper. The implementation lives in 02_mutation/pipeline/pipeline_lib.py.
import sys as _sys
from pathlib import Path as _Path


ROOT = _Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT / "02_mutation" / "pipeline"
if str(PIPELINE_DIR) not in _sys.path:
    _sys.path.insert(0, str(PIPELINE_DIR))

import argparse

from pipeline_lib import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run local exec, validate, retry with feedback, and revalidate in one pipeline."
    )
    parser.add_argument("--limit", type=int, help="Optional limit on tasks/failures")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per task in seconds")
    parser.add_argument("--max_examples", type=int, default=3, help="Max examples per failure")
    parser.add_argument("--max_attempts", type=int, default=3, help="Max LLM attempts per task")
    parser.add_argument("--report_dir", default="reports", help="Directory for JSON reports")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--include_missing", action="store_true", help="Retry missing-result failures")
    parser.add_argument("--skip_exec", action="store_true", help="Skip local execution stage")
    parser.add_argument("--skip_retry", action="store_true", help="Skip LLM feedback retry stage")
    parser.add_argument("--skip_revalidate", action="store_true", help="Skip revalidation stage")
    parser.add_argument("--skip_original", action="store_true", help="Skip original local execution")
    parser.add_argument("--stop_on_error", action="store_true", help="Stop pipeline on non-zero exit")
    args = parser.parse_args()

    run_pipeline(
        limit=args.limit,
        timeout=args.timeout,
        max_examples=args.max_examples,
        max_attempts=args.max_attempts,
        report_dir=args.report_dir,
        overwrite=args.overwrite,
        include_missing=args.include_missing,
        skip_exec=args.skip_exec,
        skip_retry=args.skip_retry,
        skip_revalidate=args.skip_revalidate,
        skip_original=args.skip_original,
        stop_on_error=args.stop_on_error,
    )


if __name__ == "__main__":
    main()
