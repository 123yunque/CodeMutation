import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rq1_config import get_mode_config, resolve_env_value, valid_modes
from rq1_utils import evaluate_mode, execute_task_with_threads, load_runtime_config


def run_llm(args):
    config = load_runtime_config()
    mode_config = get_mode_config(args.mode)
    api_key = resolve_env_value(config["api_key_fields"].get(args.mode))
    base_url = config.get("yunwu_base_url") or config.get("api_base_url")
    if not api_key:
        print(f"Missing API key for mode: {args.mode}")
        return
    if not base_url:
        print("Missing base URL. Set yunwu_base_url or api_base_url in config1.json.")
        return

    input_dir = config["input_paths"][args.mode]
    output_path = os.path.join(str(mode_config["llm_root"]), args.output_name)
    execute_task_with_threads(
        input_dir,
        output_path,
        api_key,
        base_url,
        args.model_name,
        mode_config["input_script"],
        max_workers=args.max_workers,
        overwrite=args.overwrite,
    )


def run_evaluate(args):
    modes = valid_modes() if args.mode == "all" else (args.mode,)
    results = [evaluate_mode(mode, args.output_name, write_inputs=not args.no_write_inputs) for mode in modes]

    if args.report:
        report_path = os.path.abspath(args.report)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nReport written: {report_path}")


def main(default_command=None):
    parser = argparse.ArgumentParser(description="Run or evaluate RQ1 LLM tasks.")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run RQ1 LLM output prediction tasks")
    run_parser.add_argument("--mode", required=True, choices=valid_modes(), help="Execution mode")
    run_parser.add_argument("--output_name", required=True, help="Name for the model output directory")
    run_parser.add_argument("--model_name", required=True, help="Model name for LLM API calls")
    run_parser.add_argument("--max_workers", type=int, default=2, help="Number of concurrent LLM requests")
    run_parser.add_argument("--overwrite", action="store_true", help="Regenerate outputs that already exist")
    run_parser.set_defaults(func=run_llm)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate RQ1 LLM outputs against local results")
    eval_parser.add_argument("--mode", default="all", choices=("all",) + valid_modes(), help="Mode to evaluate")
    eval_parser.add_argument("--output_name", default="gpt51", help="LLM output directory name")
    eval_parser.add_argument("--report", help="Optional JSON report path")
    eval_parser.add_argument("--no_write_inputs", action="store_true", help="Do not refresh correct/error input files")
    eval_parser.set_defaults(func=run_evaluate)

    argv = sys.argv[1:]
    if default_command and (not argv or argv[0] not in {"run", "evaluate"}):
        argv = [default_command] + argv
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
