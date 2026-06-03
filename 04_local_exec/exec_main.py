import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rq1_config import valid_modes
from exec_utils import compare_non_equivalent_results, print_compare_summary, print_exec_summary, run_mode


def main():
    parser = argparse.ArgumentParser(description="Run local RQ1 scripts and compare non-equivalent results.")
    parser.add_argument("--mode", default="original", choices=("all",) + valid_modes(), help="Execution mode")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per task in seconds")
    parser.add_argument("--limit", type=int, help="Optional number of tasks to run")
    parser.add_argument("--compare_non_equivalent", action="store_true", help="Build non-equivalent compare result files")
    args = parser.parse_args()

    modes = valid_modes() if args.mode == "all" else (args.mode,)
    for mode in modes:
        summary = run_mode(mode, args.timeout, args.limit)
        if summary:
            print_exec_summary(mode, summary)

    if args.compare_non_equivalent:
        print_compare_summary(compare_non_equivalent_results())


if __name__ == "__main__":
    main()
