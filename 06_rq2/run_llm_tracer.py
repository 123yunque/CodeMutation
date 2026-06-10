import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import sys
import threading
import time

from httpx import ConnectError, HTTPStatusError, ReadTimeout
from openai import APITimeoutError, OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import (
    CONFIG1,
    LLM_TRACE_EQUIV,
    LLM_TRACE_NON_EQUIV,
    LLM_TRACE_ORIGINAL,
    MBPP_DIR,
)
from rq1_config import resolve_env_value


ROUTES = {
    ("original", "correct"): {
        "target_file": "sample_original_correct.py",
        "output_root": LLM_TRACE_ORIGINAL,
        "api_key_field": "original",
    },
    ("original", "error"): {
        "target_file": "sample_original_error.py",
        "output_root": LLM_TRACE_ORIGINAL,
        "api_key_field": "original",
    },
    ("equivalent", "correct"): {
        "target_file": "sample_equivalent_correct.py",
        "output_root": LLM_TRACE_EQUIV,
        "api_key_field": "equivalent",
    },
    ("equivalent", "error"): {
        "target_file": "sample_equivalent_error.py",
        "output_root": LLM_TRACE_EQUIV,
        "api_key_field": "equivalent",
    },
    ("non_equivalent", "correct"): {
        "target_file": "sample_non_equivalent_correct.py",
        "output_root": LLM_TRACE_NON_EQUIV,
        "api_key_field": "non_equivalent",
    },
    ("non_equivalent", "error"): {
        "target_file": "sample_non_equivalent_error.py",
        "output_root": LLM_TRACE_NON_EQUIV,
        "api_key_field": "non_equivalent",
    },
}

thread_local = threading.local()


def get_client(api_key, base_url):
    key = (api_key, base_url)
    if getattr(thread_local, "client_key", None) != key:
        thread_local.client = OpenAI(api_key=api_key, base_url=base_url)
        thread_local.client_key = key
    return thread_local.client


def build_prompt(code_content):
    return f"""
You must execute the following Python code EXACTLY and trace all variable changes during execution.

====================
### Python Code:
{code_content}
====================

Output format (strict):
<result>
'var1': [val1, val2, val3]
'var2': [val1, val2]
...
</result>

Rules:
1. List every variable except inputs, inp, imported modules, functions, and classes.
2. Each entry shows all values the variable took during execution, in order.
3. Do not include explanations, debug info, markdown, or extra text.
4. Only return the variable sequences inside <result> ... </result>.

Now execute the code and return variable sequences ONLY in:
<result> ... </result>
"""


def call_llm(prompt, label, api_key, base_url, model_name, max_retries, timeout):
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


def extract_result_block(text):
    if not text:
        return "ERROR: empty"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def iter_folders(task=None, limit=None):
    if task:
        folders = [task]
    else:
        folders = sorted(
            path.name for path in Path(MBPP_DIR).glob("task_*")
            if path.is_dir()
        )
    if limit is not None:
        folders = folders[:limit]
    return folders


def process_task(folder, route, api_key, base_url, model_name, overwrite, max_retries, timeout):
    target_file = route["target_file"]
    src_path = Path(MBPP_DIR) / folder / target_file
    output_dir = Path(route["output_root"]) / route["status"]
    save_path = output_dir / f"{folder}.txt"
    label = f"{folder}/{target_file}"

    if not src_path.exists():
        return ("missing", f"[missing] {label}")
    if save_path.exists() and not overwrite:
        return ("skipped", f"[skip] {label}: {save_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    code_content = src_path.read_text(encoding="utf-8")
    prompt = build_prompt(code_content)
    llm_output = call_llm(prompt, label, api_key, base_url, model_name, max_retries, timeout)
    final_result = extract_result_block(llm_output)
    save_path.write_text(final_result, encoding="utf-8")

    if final_result.startswith("ERROR:"):
        return ("failed", f"[failed] {label}: {final_result}")
    return ("success", f"[done] {label}: {save_path}")


def selected_routes(mode, status):
    modes = ("original", "equivalent", "non_equivalent") if mode == "all" else (mode,)
    statuses = ("correct", "error") if status == "all" else (status,)
    routes = []
    for route_mode in modes:
        for route_status in statuses:
            route = dict(ROUTES[(route_mode, route_status)])
            route["mode"] = route_mode
            route["status"] = route_status
            routes.append(route)
    return routes


def run(args, config):
    api_key_fields = config["api_key_fields"]
    base_url = args.base_url or config.get("yunwu_base_url") or config.get("api_base_url")
    model_name = args.model_name or config.get("model_name")
    if not model_name:
        raise ValueError("Missing model name. Pass --model_name or set model_name in config1.json.")
    if not base_url:
        raise ValueError("Missing API base URL. Pass --base_url or set yunwu_base_url/api_base_url in config1.json.")

    folders = iter_folders(task=args.task, limit=args.limit)
    routes = selected_routes(args.mode, args.status)
    jobs = []
    for route in routes:
        api_key = resolve_env_value(api_key_fields[route["api_key_field"]])
        if not api_key:
            raise ValueError(f"Missing API key for {route['api_key_field']}. Check config1.json/env vars.")
        for folder in folders:
            jobs.append((folder, route, api_key))

    print(f"LLM trace run: model={model_name}, base_url={base_url}, jobs={len(jobs)}")
    stats = {"success": 0, "failed": 0, "missing": 0, "skipped": 0}

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = [
            executor.submit(
                process_task,
                folder,
                route,
                api_key,
                base_url,
                model_name,
                args.overwrite,
                args.max_retries,
                args.timeout,
            )
            for folder, route, api_key in jobs
        ]
        for future in as_completed(futures):
            status, message = future.result()
            stats[status] += 1
            print(message)

    print(
        f"Done. success={stats['success']}, failed={stats['failed']}, "
        f"missing={stats['missing']}, skipped={stats['skipped']}"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate LLM-predicted RQ2 variable traces.")
    parser.add_argument("--model_name", help="Defaults to config1.json model_name")
    parser.add_argument("--base_url", help="Defaults to config1.json yunwu_base_url/api_base_url")
    parser.add_argument("--mode", choices=("all", "original", "equivalent", "non_equivalent"), default="all")
    parser.add_argument("--status", choices=("all", "correct", "error"), default="all")
    parser.add_argument("--task", help="Optional task folder name, for example task_142")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max_workers", type=int, default=1)
    parser.add_argument("--max_retries", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    config = json.loads(Path(CONFIG1).read_text(encoding="utf-8"))
    run(args, config)


if __name__ == "__main__":
    main()
