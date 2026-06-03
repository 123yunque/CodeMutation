import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import MBPP_DIR
from data_utils import generate_dataset, read_model_footer


def main():
    parser = argparse.ArgumentParser(description="Load MBPP++ tasks into the project task directory.")
    parser.add_argument("--output_dir", default=str(MBPP_DIR), help="Output task directory")
    parser.add_argument("--sample_size", type=int, default=10, help="Number of sampled inputs per task")
    parser.add_argument("--seed", type=int, default=0, help="Random seed for sampled inputs")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing task directories")
    parser.add_argument("--limit", type=int, help="Optional task limit for quick checks")
    args = parser.parse_args()

    model_path = Path(__file__).resolve().parent / "model.py"
    stats = generate_dataset(
        args.output_dir,
        read_model_footer(str(model_path)),
        sample_size=args.sample_size,
        seed=args.seed,
        overwrite=args.overwrite,
        limit=args.limit,
    )
    print(f"Done. written={stats['written']}, skipped={stats['skipped']}, failed={stats['failed']}")


if __name__ == "__main__":
    main()
