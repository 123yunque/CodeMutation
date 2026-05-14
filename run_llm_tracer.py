# batch_llm_tracer.py
import json
import os
import threading
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI, APITimeoutError
from httpx import ReadTimeout, ConnectError, HTTPStatusError

# ================= 配置区 =================
INPUT_DIR = "output_mbppplus_new"

"""
让LLM给变量变化序列
"""
# 目标文件 -> (输出基目录, 输出子目录, api_key_fields中的key)
FILE_CONFIG = {
    "sample_original_correct.py":       ("original_llm",       "correct", "original"),
    "sample_original_error.py":         ("original_llm",       "error",   "original"),
    "sample_equivalent_correct.py":     ("equivalent_llm",     "correct", "equivalent"),
    "sample_equivalent_error.py":       ("equivalent_llm",     "error",   "equivalent"),
    "sample_non_equivalent_correct.py": ("non_equivalent_llm", "correct", "non_equivalent"),
    "sample_non_equivalent_error.py":   ("non_equivalent_llm", "error",   "non_equivalent"),
}
# ==========================================

thread_local = threading.local()

def get_client(api_key, base_url="https://api3.wlai.vip/v1"):
    if not hasattr(thread_local, "client"):
        thread_local.client = OpenAI(api_key=api_key, base_url=base_url)
    return thread_local.client

def call_llm(prompt, label, api_key, model_name, max_retries=5):
    messages = [
        {"role": "system", "content": "Return ONLY the final result. No explanation."},
        {"role": "user", "content": prompt}
    ]
    for attempt in range(max_retries):
        try:
            client = get_client(api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                timeout=240
            )
            content = response.choices[0].message.content
            if content.strip():
                return content
            print(f"⚠️ {label} 空内容 attempt={attempt + 1}")
        except (APITimeoutError, ReadTimeout):
            print(f"⏳ Timeout {label}, attempt={attempt + 1}")
        except (ConnectError, HTTPStatusError, Exception) as e:
            print(f"⚠️ Error {label}: {e} attempt={attempt + 1}")
        time.sleep(2 ** attempt)
    print(f"❌ {label} 连续失败")
    return None

def extract_result_block(text):
    if not text:
        return "ERROR: empty"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

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
1. List every variable (except: inputs, inp, imported modules, functions, classes).
2. Each entry shows ALL values the variable took during execution, in order.
3. Do NOT include any explanations, debug info, or extra text.
4. Only return the variable sequences inside <result> ... </result>.

Example:
<result>
'a': [1, 3, 7, 15]
'b': [2, 4, 8, 16]
'i': [0, 1, 2]
</result>

Now execute the code and return variable sequences ONLY in:
<result> ... </result>
"""

def process_task(folder, target_file, output_dir, api_key, model_name):
    label = f"{folder}/{target_file}"
    save_file = os.path.join(output_dir, f"{folder}.txt")

    if os.path.exists(save_file):
        return f"⏭️ 已存在，跳过 {label}"

    src_path = os.path.join(INPUT_DIR, folder, target_file)
    if not os.path.exists(src_path):
        return f"⚠️ 文件不存在: {src_path}"

    with open(src_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    prompt = build_prompt(code_content)
    llm_output = call_llm(prompt, label, api_key, model_name)
    final_result = extract_result_block(llm_output)

    with open(save_file, "w", encoding="utf-8") as f:
        f.write(final_result)

    return f"✅ 完成: {label}"


def run_single_file_type(target_file, output_dir, api_key, model_name, folders):
    """单个文件类型的串行处理，供线程池调用"""
    success, fail = 0, 0
    for folder in folders:
        result = process_task(folder, target_file, output_dir, api_key, model_name)
        print(result)
        if result.startswith("✅"):
            success += 1
        else:
            fail += 1
    return f"[{target_file}] 完成: 成功 {success}，失败/跳过 {fail}"


def run(model_name, api_key_fields):
    folders = sorted([
        f for f in os.listdir(INPUT_DIR)
        if os.path.isdir(os.path.join(INPUT_DIR, f)) and f.startswith("task_")
    ])
    print(f"🔍 找到 {len(folders)} 个 task 文件夹")

    # 预创建输出目录，构建每路任务参数
    routes = []
    for target_file, (base, sub, api_key_field) in FILE_CONFIG.items():
        out_dir = os.path.join(base, sub)
        os.makedirs(out_dir, exist_ok=True)
        api_key = api_key_fields[api_key_field]
        routes.append((target_file, out_dir, api_key))

    print(f"🚀 启动 {len(routes)} 路并发，每路处理 {len(folders)} 个 task\n")

    # 6路并发，每路负责一种文件类型，内部串行
    with ThreadPoolExecutor(max_workers=len(routes)) as executor:
        futures = {
            executor.submit(run_single_file_type, target_file, out_dir, api_key, model_name, folders): target_file
            for target_file, out_dir, api_key in routes
        }
        for future in as_completed(futures):
            print(f"\n🏁 {future.result()}")

    print("\n🎉 全部处理完成！")


def main():
    with open("config1.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", required=True, help="LLM 模型名称")
    args = parser.parse_args()

    run(args.model_name, config["api_key_fields"])

if __name__ == "__main__":
    main()