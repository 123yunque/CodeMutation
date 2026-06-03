import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from splice_utils import splice_mode


def main(default_mode=None):
    parser = argparse.ArgumentParser(description="Build executable sample scripts for RQ1 tasks.")
    parser.add_argument(
        "--mode",
        choices=("original", "equivalent", "non_equivalent", "all"),
        default=default_mode or "all",
        help="Which sample scripts to generate",
    )
    args = parser.parse_args()

    results = splice_mode(args.mode)
    for mode, stats in results.items():
        print(f"Done {mode}. written={stats['written']}, missing={stats['missing']}")


if __name__ == "__main__":
    main()
