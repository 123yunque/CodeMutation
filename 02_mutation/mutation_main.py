import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mutation_utils import prompt_builder_for_mode, run_mutation


def main(default_mode=None):
    parser = argparse.ArgumentParser(description="Generate equivalent or non-equivalent mutations.")
    parser.add_argument("--mode", choices=("equivalent", "non_equivalent"), default=default_mode, required=default_mode is None)
    parser.add_argument("--model_name", help="Override model name from config1.json")
    parser.add_argument("--max_workers", type=int, default=2, help="Concurrent LLM requests")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing outputs")
    parser.add_argument("--limit", type=int, help="Optional task limit for quick checks")
    parser.add_argument("--no_validate", action="store_true", help="Skip generated Python syntax validation")
    args = parser.parse_args()

    run_mutation(
        mode=args.mode,
        prompt_builder=prompt_builder_for_mode(args.mode),
        model_name=args.model_name,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
        limit=args.limit,
        validate=not args.no_validate,
    )


if __name__ == "__main__":
    main()
