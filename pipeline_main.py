import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent

from pipeline_lib import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Validate existing RQ1 local outputs, with optional local execution and mutation retry."
    )
    parser.add_argument("--limit", type=int, help="Optional limit on tasks/failures")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per task in seconds")
    parser.add_argument("--max_examples", type=int, default=3, help="Max examples per failure")
    parser.add_argument("--max_attempts", type=int, default=3, help="Max LLM attempts per task")
    parser.add_argument("--report_dir", default="reports", help="Directory for JSON reports")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--include_missing", action="store_true", help="Retry missing-result failures")
    parser.add_argument("--run_exec", action="store_true", help="Run local execution before validation")
    parser.add_argument("--retry", action="store_true", help="Retry failed mutations with LLM feedback")
    parser.add_argument("--no_revalidate_after_retry", action="store_true", help="Do not revalidate after retry")
    parser.add_argument("--skip_original", action="store_true", help="Skip original local execution when --run_exec is set")
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
        run_exec=args.run_exec,
        retry=args.retry,
        revalidate_after_retry=not args.no_revalidate_after_retry,
        skip_original=args.skip_original,
        stop_on_error=args.stop_on_error,
    )


if __name__ == "__main__":
    main()
