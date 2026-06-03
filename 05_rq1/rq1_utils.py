import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from paths import CONFIG1, MBPP_DIR
from rq1_config import get_mode_config


INVALID_LOCAL_RESULT = "变异前后结果相同，认为该测试用例无效"


def load_runtime_config():
    with open(str(CONFIG1), "r", encoding="utf-8") as f:
        return json.load(f)


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
    if not api_key:
        raise ValueError("api_key is required")
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
        {"role": "system", "content": "Return ONLY the final result. No explanation."},
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

    print(f"[failed] {folder} exceeded retry limit")
    return None


def extract_result_block(text):
    if not text:
        return "ERROR: empty"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def build_execution_prompt(code_content):
    return f"""
You must execute the following Python code EXACTLY and return only the final results.

====================
### Python Code:
{code_content}
====================

Output format (strict):
<result>
line1
line2
...
</result>

Rules:
1. If the code produces no output, you must still return one empty line between <result> tags.
2. Do NOT include any explanations, debug info, or extra text.
3. Only return results in the <result> ... </result> block.

Now execute the code and return results ONLY in:
<result> ... </result>
"""


def process_llm_task(folder, input_dir, output_path, api_key, base_url, model_name, input_file_name, overwrite=False):
    save_file = os.path.join(output_path, f"{folder}.txt")
    if os.path.exists(save_file) and not overwrite:
        return f"[skip] output exists: {folder}"

    sub_dir = os.path.join(input_dir, folder)
    if not os.path.isdir(sub_dir):
        return f"[skip] not a task directory: {folder}"

    input_file = os.path.join(sub_dir, input_file_name)
    if not os.path.exists(input_file):
        return f"[missing] {input_file}"

    with open(input_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    llm_output = call_llm(build_execution_prompt(code_content), folder, api_key, base_url, model_name)
    final_result = extract_result_block(llm_output)

    with open(save_file, "w", encoding="utf-8") as f:
        f.write(final_result)

    return f"[done] {folder}"


def execute_task_with_threads(input_dir, output_path, api_key, base_url, model_name, input_file_name, max_workers=2, overwrite=False):
    os.makedirs(output_path, exist_ok=True)
    folders = [f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))]
    print(f"Processing {len(folders)} tasks with max_workers={max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [
            executor.submit(
                process_llm_task,
                folder,
                input_dir,
                output_path,
                api_key,
                base_url,
                model_name,
                input_file_name,
                overwrite,
            )
            for folder in folders
        ]
        for future in as_completed(tasks):
            print(future.result())


def read_lines(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def compare_outputs(llm_lines, local_lines):
    pairs = []
    for index, local_line in enumerate(local_lines):
        if local_line == INVALID_LOCAL_RESULT:
            continue
        llm_line = llm_lines[index] if index < len(llm_lines) else None
        pairs.append({"line": index + 1, "llm": llm_line, "local": local_line, "same": llm_line == local_line})

    same_count = sum(1 for item in pairs if item["same"])
    missing_output_lines = sum(1 for item in pairs if item["llm"] is None)
    extra_output_lines = max(0, len(llm_lines) - len(local_lines))

    if not pairs:
        status = "no_valid_cases"
    elif same_count == len(pairs):
        status = "full_same"
    elif same_count == 0:
        status = "all_diff"
    else:
        status = "partial_same"

    return {
        "pairs": pairs,
        "same_count": same_count,
        "total_count": len(pairs),
        "diff_lines": [item["line"] for item in pairs if not item["same"]],
        "missing_output_lines": missing_output_lines,
        "extra_output_lines": extra_output_lines,
        "status": status,
    }


def write_first_case_inputs(task_dir, input_lines, comparison, correct_name, error_name):
    correct_path = os.path.join(task_dir, correct_name)
    error_path = os.path.join(task_dir, error_name)

    if os.path.exists(correct_path):
        os.remove(correct_path)
    if os.path.exists(error_path):
        os.remove(error_path)

    first_same = next((item for item in comparison["pairs"] if item["same"]), None)
    first_diff = next((item for item in comparison["pairs"] if not item["same"]), None)

    if first_same:
        input_line = input_lines[first_same["line"] - 1] if first_same["line"] - 1 < len(input_lines) else ""
        with open(correct_path, "w", encoding="utf-8") as f:
            f.write(f"{input_line}\n")

    if first_diff:
        input_line = input_lines[first_diff["line"] - 1] if first_diff["line"] - 1 < len(input_lines) else ""
        with open(error_path, "w", encoding="utf-8") as f:
            f.write(f"{input_line}\n")


def empty_summary():
    return {
        "task_count": 0,
        "valid_task_count": 0,
        "same_cases": 0,
        "total_cases": 0,
        "accuracy": 0.0,
        "full_same_tasks": 0,
        "partial_same_tasks": 0,
        "all_diff_tasks": 0,
        "missing_file_tasks": 0,
        "no_valid_case_tasks": 0,
        "missing_output_lines": 0,
        "extra_output_lines": 0,
    }


def summarize(task_results):
    summary = empty_summary()
    summary["task_count"] = len(task_results)

    for result in task_results:
        status = result["status"]
        if status == "missing_file":
            summary["missing_file_tasks"] += 1
            continue
        if status == "no_valid_cases":
            summary["no_valid_case_tasks"] += 1
            continue

        summary["valid_task_count"] += 1
        summary["same_cases"] += result["same_count"]
        summary["total_cases"] += result["total_count"]
        summary["missing_output_lines"] += result["missing_output_lines"]
        summary["extra_output_lines"] += result["extra_output_lines"]

        if status == "full_same":
            summary["full_same_tasks"] += 1
        elif status == "partial_same":
            summary["partial_same_tasks"] += 1
        elif status == "all_diff":
            summary["all_diff_tasks"] += 1

    if summary["total_cases"]:
        summary["accuracy"] = summary["same_cases"] / summary["total_cases"]
    return summary


def evaluate_mode(mode, output_name, write_inputs=True):
    mode_config = get_mode_config(mode)
    llm_dir = os.path.join(str(mode_config["llm_root"]), output_name)
    task_root = str(MBPP_DIR)

    if not os.path.exists(llm_dir):
        print(f"[missing] LLM output directory does not exist: {llm_dir}")
        return {"mode": mode, "output_name": output_name, "tasks": [], "summary": empty_summary()}

    task_results = []
    for fname in sorted(os.listdir(llm_dir)):
        if not fname.startswith("task_") or not fname.endswith(".txt"):
            continue

        task_id = fname[:-4]
        task_dir = os.path.join(task_root, task_id)
        llm_path = os.path.join(llm_dir, fname)
        local_path = os.path.join(task_dir, mode_config["local_result"])
        input_path = os.path.join(task_dir, "sample_code_inputs.txt")

        llm_lines = read_lines(llm_path)
        local_lines = read_lines(local_path)
        input_lines = read_lines(input_path)

        if llm_lines is None or local_lines is None or input_lines is None:
            missing = []
            if llm_lines is None:
                missing.append(llm_path)
            if local_lines is None:
                missing.append(local_path)
            if input_lines is None:
                missing.append(input_path)
            task_results.append(
                {
                    "task_id": task_id,
                    "status": "missing_file",
                    "missing": missing,
                    "same_count": 0,
                    "total_count": 0,
                    "diff_lines": [],
                    "missing_output_lines": 0,
                    "extra_output_lines": 0,
                }
            )
            continue

        comparison = compare_outputs(llm_lines, local_lines)
        if write_inputs:
            write_first_case_inputs(
                task_dir,
                input_lines,
                comparison,
                mode_config["correct_input"],
                mode_config["error_input"],
            )

        task_results.append(
            {
                "task_id": task_id,
                "status": comparison["status"],
                "same_count": comparison["same_count"],
                "total_count": comparison["total_count"],
                "diff_lines": comparison["diff_lines"],
                "missing_output_lines": comparison["missing_output_lines"],
                "extra_output_lines": comparison["extra_output_lines"],
            }
        )

    summary = summarize(task_results)
    print_mode_summary(mode, output_name, summary, task_results)
    return {"mode": mode, "output_name": output_name, "tasks": task_results, "summary": summary}


def print_mode_summary(mode, output_name, summary, task_results):
    print(f"\n===== RQ1 {mode} / {output_name} =====")
    print(f"Tasks scanned: {summary['task_count']}")
    print(f"Valid tasks: {summary['valid_task_count']}")
    print(f"Same cases: {summary['same_cases']} / {summary['total_cases']}")
    print(f"Accuracy: {summary['accuracy']:.2%}")
    print(f"Full same tasks: {summary['full_same_tasks']}")
    print(f"Partial same tasks: {summary['partial_same_tasks']}")
    print(f"All diff tasks: {summary['all_diff_tasks']}")
    print(f"Missing-file tasks: {summary['missing_file_tasks']}")
    print(f"No-valid-case tasks: {summary['no_valid_case_tasks']}")
    print(f"Missing output lines: {summary['missing_output_lines']}")
    print(f"Extra output lines: {summary['extra_output_lines']}")

    missing = [item["task_id"] for item in task_results if item["status"] == "missing_file"]
    if missing:
        print(f"Missing-file task ids: {', '.join(missing)}")
