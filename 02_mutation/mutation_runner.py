# [auto-patched by patch_imports.py]
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).parent.parent))

from config_loader import load_config
from paths import EQUIV_TRANSFORM, MBPP_DIR, NON_EQUIV_TRANSFORM

import ast
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


MODE_OUTPUTS = {
    "equivalent": EQUIV_TRANSFORM,
    "non_equivalent": NON_EQUIV_TRANSFORM,
}

thread_local = threading.local()


class LegacyOpenAIClient:
    def __init__(self, openai_module, api_key, base_url):
        self.openai = openai_module
        self.openai.api_key = api_key
        self.openai.api_base = base_url

    def create_chat_completion(self, model_name, messages, timeout):
        return self.openai.ChatCompletion.create(
            model=model_name,
            messages=messages,
            request_timeout=timeout,
        )


class ModernOpenAIClient:
    def __init__(self, client):
        self.client = client

    def create_chat_completion(self, model_name, messages, timeout):
        return self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=timeout,
        )


def get_client(api_key, base_url):
    if not hasattr(thread_local, "client"):
        import openai

        if hasattr(openai, "OpenAI"):
            thread_local.client = ModernOpenAIClient(openai.OpenAI(api_key=api_key, base_url=base_url))
        elif hasattr(openai, "ChatCompletion"):
            thread_local.client = LegacyOpenAIClient(openai, api_key, base_url)
        else:
            raise RuntimeError("Unsupported openai SDK: missing OpenAI and ChatCompletion clients")
    return thread_local.client


def get_response_content(response):
    if hasattr(response, "choices"):
        return response.choices[0].message.content
    return response["choices"][0]["message"]["content"]


def call_llm(prompt, folder, api_key, base_url, model_name, max_retries=5):
    messages = [
        {"role": "system", "content": "Return ONLY the modified code, no explanation, no reasoning."},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(max_retries):
        try:
            client = get_client(api_key, base_url)
            response = client.create_chat_completion(model_name, messages, timeout=240)
            content = get_response_content(response)
            if content and content.strip():
                return content
            print(f"[empty] {folder} attempt={attempt + 1}")
        except Exception as exc:
            print(f"[error] {folder} attempt={attempt + 1}: {exc}")
        time.sleep(2 ** attempt)

    return None


def extract_result_block(text):
    if not text:
        return "ERROR: LLM returned no result"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def validate_python_code(code_text):
    try:
        ast.parse(code_text)
    except SyntaxError as exc:
        return False, f"{exc.msg} at line {exc.lineno}"
    return True, ""


def read_code(task_dir):
    code_path = os.path.join(task_dir, "code.py")
    if not os.path.exists(code_path):
        return None
    with open(code_path, "r", encoding="utf-8") as f:
        return f.read()


def process_folder(
    folder,
    input_dir,
    output_dir,
    prompt_builder,
    api_key,
    base_url,
    model_name,
    overwrite=False,
    validate=True,
):
    save_file = os.path.join(output_dir, f"{folder}.py")
    if os.path.exists(save_file) and not overwrite:
        return f"[skip] output exists: {folder}"

    task_dir = os.path.join(input_dir, folder)
    if not os.path.isdir(task_dir):
        return f"[skip] not a task directory: {folder}"

    code_content = read_code(task_dir)
    if code_content is None:
        return f"[missing] {folder}/code.py"

    llm_output = call_llm(
        prompt_builder(code_content),
        folder,
        api_key,
        base_url,
        model_name,
    )
    final_result = extract_result_block(llm_output)

    if validate:
        is_valid, error = validate_python_code(final_result)
        if not is_valid:
            return f"[invalid] {folder}: {error}"

    with open(save_file, "w", encoding="utf-8") as f:
        f.write(final_result)
    return f"[done] {folder}"


def iter_folders(input_dir, limit=None):
    folders = sorted(f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f)))
    if limit is not None:
        return folders[:limit]
    return folders


def run_mutation(
    mode,
    prompt_builder,
    output_dir=None,
    input_dir=None,
    model_name=None,
    api_key=None,
    base_url=None,
    max_workers=2,
    overwrite=False,
    limit=None,
    validate=True,
):
    config = load_config()
    input_dir = input_dir or str(MBPP_DIR)
    output_dir = output_dir or str(MODE_OUTPUTS[mode])
    model_name = model_name or config.get("model_name", "gpt-5.1")
    api_key = api_key or config["api_key_fields"][mode]
    base_url = base_url or config.get("yunwu_base_url") or config.get("api_base_url")

    if not api_key:
        raise ValueError(f"Missing API key for mode: {mode}")
    if not base_url:
        raise ValueError("Missing base URL. Set yunwu_base_url or api_base_url in config1.json.")

    os.makedirs(output_dir, exist_ok=True)
    folders = iter_folders(input_dir, limit)
    print(f"Running mutation mode={mode}, tasks={len(folders)}, model={model_name}, max_workers={max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_folder,
                folder,
                input_dir,
                output_dir,
                prompt_builder,
                api_key,
                base_url,
                model_name,
                overwrite,
                validate,
            )
            for folder in folders
        ]
        for future in as_completed(futures):
            print(future.result())
