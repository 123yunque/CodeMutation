# Compatibility wrapper. The implementation lives in 02_mutation/pipeline/pipeline_lib.py.
import sys as _sys
from pathlib import Path as _Path


ROOT = _Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT / "02_mutation" / "pipeline"
if str(PIPELINE_DIR) not in _sys.path:
    _sys.path.insert(0, str(PIPELINE_DIR))

import argparse

from pipeline_lib import validate_mutations


def main():
    parser = argparse.ArgumentParser(description="Validate mutation outputs and include failure examples.")
    parser.add_argument(
        "--mode",
        default="all",
        choices=("all", "equivalent", "non_equivalent"),
        help="Which mutation type to validate",
    )
    parser.add_argument("--limit", type=int, help="Optional limit on number of tasks")
    parser.add_argument("--max_examples", type=int, default=3, help="Max example lines per failing task")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()

    validate_mutations(args.report, args.limit, args.max_examples, mode=args.mode)


if __name__ == "__main__":
    main()
