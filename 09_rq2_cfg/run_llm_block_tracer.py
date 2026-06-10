import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import sys
import threading
import time

from httpx import ConnectError, HTTPStatusError, ReadTimeout
from openai import APITimeoutError, OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfg_builder import blocks_from_dict, build_cfg, format_cfg_for_prompt
from paths import CONFIG1, MBPP_DIR, ROOT
from rq1_config import resolve_env_value


FILE_CONFIG = {
    "sample_original_correct.py": {
        "llm_dir": ROOT / "block_original_llm" / "correct",
        "local_dir": ROOT / "block_original_local" / "correct",
        "api_key_field": "original",
    },
    "sample_original_error.py": {
        "llm_dir": ROOT / "block_original_llm" / "error",
        "local_dir": ROOT / "block_original_local" / "error",
        "api_key_field": "original",
    },
    "sample_equivalent_correct.py": {
        "llm_dir": ROOT / "block_equivalent_llm" / "correct",
        "local_dir": ROOT / "block_equivalent_local" / "correct",
        "api_key_field": "equivalent",
    },
    "sample_equivalent_error.py": {
        "llm_dir": ROOT / "block_equivalent_llm" / "error",
        "local_dir": ROOT / "block_equivalent_local" / "error",
        "api_key_field": "equivalent",
    },
    "sample_non_equivalent_correct.py": {
        "llm_dir": ROOT / "block_non_equivalent_llm" / "correct",
        "local_dir": ROOT / "block_non_equivalent_local" / "correct",
        "api_key_field": "non_equivalent",
    },
    "sample_non_equivalent_error.py": {
        "llm_dir": ROOT / "block_non_equivalent_llm" / "error",
        "local_dir": ROOT / "block_non_equivalent_local" / "error",
        "api_key_field": "non_equivalent",
    },
}

thread_local = threading.local()


def get_client(api_key: str, base_url: str) -> OpenAI:
    key = (api_key, base_url)
    if getattr(thread_local, "client_key", None) != key:
        thread_local.client = OpenAI(api_key=api_key, base_url=base_url)
        thread_local.client_key = key
    return thread_local.client


def call_llm(
    prompt: str,
    label: str,
    api_key: str,
    base_url: str,
    model_name: str,
    max_retries: int,
    timeout: int,
) -> str | None:
    messages = [
        {"role": "system", "content": "Return only the requested result. No explanation."},
        {"role": "user", "content": prompt},
    ]
    for attempt in range(1, max_retries + 1):
        try:
            client = get_client(api_key, base_url)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                timeout=timeout,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content
            print(f"[empty] {label}, attempt={attempt}")
        except (APITimeoutError, ReadTimeout):
            print(f"[timeout] {label}, attempt={attempt}")
        except (ConnectError, HTTPStatusError, Exception) as exc:
            print(f"[error] {label}: {exc}, attempt={attempt}")
        if attempt < max_retries:
            time.sleep(2 ** (attempt - 1))
    return None


def extract_result_block(text: str | None) -> str:
    if not text:
        return "ERROR: empty"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def build_block_trace_prompt(source_code: str, cfg_text: str, output_var: str) -> str:
    return f"""The following Python code has been divided into CFG basic blocks.

CFG:
{cfg_text}

Complete Python code:
```python
{source_code}
```

Simulate the execution and predict:
1. The exact executed block sequence. Repeated loop visits must be listed.
2. The variable `{output_var}` values when entering a new block, recording only changed values.

Return strictly in this format, with no explanation:
<result>
'block_sequence': ['B0', 'B1']
'{output_var}': [None, 0]
</result>
"""


def iter_tasks(task: str | None, limit: int | None):
    if task:
        tasks = [task]
    else:
        tasks = sorted(path.name for path in Path(MBPP_DIR).glob("task_*") if path.is_dir())
    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def selected_files(mode: str, status: str):
    modes = ("original", "equivalent", "non_equivalent") if mode == "all" else (mode,)
    statuses = ("correct", "error") if status == "all" else (status,)
    for selected_mode in modes:
        for selected_status in statuses:
            target_file = f"sample_{selected_mode}_{selected_status}.py"
            yield target_file, FILE_CONFIG[target_file]


def load_cfg_text(source_code: str, cfg_json_path: Path) -> tuple[str, str]:
    if cfg_json_path.exists():
        cfg_data = json.loads(cfg_json_path.read_text(encoding="utf-8"))
        output_var = cfg_data.get("output_var", "result")
        blocks = blocks_from_dict(cfg_data.get("blocks", {}))
        return output_var, format_cfg_for_prompt(blocks)

    _, blocks = build_cfg(source_code)
    return "result", format_cfg_for_prompt(blocks)


def process_task(
    folder: str,
    target_file: str,
    route: dict,
    api_key: str,
    base_url: str,
    model_name: str,
    overwrite: bool,
    max_retries: int,
    timeout: int,
) -> tuple[str, str]:
    source_path = Path(MBPP_DIR) / folder / target_file
    output_dir = route["llm_dir"]
    save_path = output_dir / f"{folder}.txt"
    label = f"{folder}/{target_file}"

    if not source_path.exists():
        return "missing", f"[missing] {label}"
    if save_path.exists() and not overwrite:
        return "skipped", f"[skip] {label}"

    output_dir.mkdir(parents=True, exist_ok=True)
    source_code = source_path.read_text(encoding="utf-8")
    output_var, cfg_text = load_cfg_text(
        source_code,
        route["local_dir"] / f"{folder}_cfg.json",
    )
    prompt = build_block_trace_prompt(source_code, cfg_text, output_var)
    final_result = extract_result_block(
        call_llm(prompt, label, api_key, base_url, model_name, max_retries, timeout)
    )
    save_path.write_text(final_result, encoding="utf-8")

    if final_result.startswith("ERROR:"):
        return "failed", f"[failed] {label}: {final_result}"
    return "success", f"[done] {label}: {save_path}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM-predicted RQ2 CFG block traces.")
    parser.add_argument("--model_name", help="Defaults to config1.json model_name")
    parser.add_argument("--base_url", help="Defaults to config1.json yunwu_base_url/api_base_url")
    parser.add_argument("--mode", choices=("all", "original", "equivalent", "non_equivalent"), default="all")
    parser.add_argument("--status", choices=("all", "correct", "error"), default="all")
    parser.add_argument("--task", help="Optional task folder name, for example task_100")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max_workers", type=int, default=6)
    parser.add_argument("--max_retries", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    config = json.loads(Path(CONFIG1).read_text(encoding="utf-8"))
    api_key_fields = config["api_key_fields"]
    base_url = args.base_url or config.get("yunwu_base_url") or config.get("api_base_url")
    model_name = args.model_name or config.get("model_name")
    if not base_url:
        raise ValueError("Missing API base URL.")
    if not model_name:
        raise ValueError("Missing model name.")

    jobs = []
    folders = iter_tasks(args.task, args.limit)
    for target_file, route in selected_files(args.mode, args.status):
        api_key = resolve_env_value(api_key_fields[route["api_key_field"]])
        if not api_key:
            raise ValueError(f"Missing API key for {route['api_key_field']}.")
        for folder in folders:
            jobs.append((folder, target_file, route, api_key))

    print(f"LLM CFG block trace run: model={model_name}, jobs={len(jobs)}")
    stats = {"success": 0, "failed": 0, "missing": 0, "skipped": 0}
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = [
            executor.submit(
                process_task,
                folder,
                target_file,
                route,
                api_key,
                base_url,
                model_name,
                args.overwrite,
                args.max_retries,
                args.timeout,
            )
            for folder, target_file, route, api_key in jobs
        ]
        for future in as_completed(futures):
            status, message = future.result()
            stats[status] += 1
            print(message)

    print(
        f"Done. success={stats['success']}, failed={stats['failed']}, "
        f"missing={stats['missing']}, skipped={stats['skipped']}"
    )


if __name__ == "__main__":
    main()
