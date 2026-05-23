import json
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI, APITimeoutError
from httpx import ReadTimeout, ConnectError, HTTPStatusError

API_BASE_URL = "https://api3.wlai.vip/v1"

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
output_path = os.path.join(current_dir, "sample_output_LLMs_original_code", "gpt4o-mini")
input_dir = os.path.join(current_dir, "output_mbppplus_new")
model_name = "gpt-4o-mini"

# =====================================
#   Thread-local client (线程安全)
# =====================================
thread_local = threading.local()

def get_client(api_key):
    if not hasattr(thread_local, "client"):
        thread_local.client = OpenAI(api_key=api_key, base_url=API_BASE_URL)
    return thread_local.client


# =====================================
#        调用 LLM（指数退避重试）
# =====================================
def call_llm(prompt, folder, api_key, max_retries=5):
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

            if not response or not response.choices:
                print(f"⚠️ {folder} 无效响应 attempt={attempt+1}")
                continue

            content = response.choices[0].message.content
            if not content.strip():
                print(f"⚠️ {folder} 空内容 attempt={attempt+1}")
                continue

            return content

        except (APITimeoutError, ReadTimeout):
            print(f"⏳ Timeout {folder} attempt={attempt+1}")
        except (HTTPStatusError, ConnectError, Exception) as e:
            print(f"⚠️ Error {folder} attempt={attempt+1}: {e}")

        # 指数退避
        time.sleep(2 ** attempt)

    print(f"❌ {folder} 连续失败")
    return None


# =====================================
#          提取结果块
# =====================================
def extract_result_block(text):
    if not text:
        return "ERROR: empty"

    pat = r"<result>(.*?)</result>"
    m = re.search(pat, text, re.DOTALL)
    if m:
        return m.group(1).strip()

    return text.strip()


# =====================================
#         处理单个任务
# =====================================
def process_folder(folder, api_key):
    sub_dir = os.path.join(input_dir, folder)

    # 跳过部分任务（数字小于 224）
    if folder.startswith("task_"):
        try:
            num = int(folder.split("_")[1])
            if num > 224:
                return f"⏭ 跳过 {folder}"
        except:
            pass

    if not os.path.isdir(sub_dir):
        return f"⏭ 非文件夹 {folder}"

    combined_file = os.path.join(sub_dir, "new_sample_inputs.py")
    if not os.path.exists(combined_file):
        return f"⚠️ 无 new_sample_inputs.py: {folder}"

    with open(combined_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    prompt = f"""
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

Example:
<result>
3
7
</result>

Now execute the code and return results ONLY in:
<result> ... </result>
"""

    print(f"🧠 调用模型: {folder} ...")

    llm_output = call_llm(prompt, folder, api_key)
    final_result = extract_result_block(llm_output)

    save_file = os.path.join(output_path, f"{folder}.txt")
    with open(save_file, "w", encoding="utf-8") as f:
        f.write(final_result)

    return f"✅ 完成：{folder}"


# =====================================
#          主调度（高并发）
# =====================================

# def generate_results(api_key):
#     if not os.path.exists(output_path):
#         os.makedirs(output_path, exist_ok=True)
#
#     folders = [f for f in os.listdir(input_dir)]
#
#     print(f"🚀 开始并发处理，总共 {len(folders)} 个任务")
#
#     # ✨ 并发数量 = CPU 核心数 × 4
#     max_workers = os.cpu_count() / 2
#     print(f"🔥 使用并发线程数: {max_workers}")
#
#     processed_count = 0   # ✅ 新增：统计处理数量
#     max_process = 10      # ✅ 新增：最多处理 10 个
#
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         futures = {executor.submit(process_folder, folder, api_key): folder for folder in folders}
#
#         for future in as_completed(futures):
#
#             print(future.result())
#             processed_count += 1
#
#             if processed_count >= max_process:
#                 print(f"🛑 已处理 {processed_count} 个任务，达到上限，停止程序")
#                 executor.shutdown(wait=False, cancel_futures=True)
#                 return

def generate_results(api_key):
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)

    folders = [f for f in os.listdir(input_dir)]

    print(f"🚀 开始并发处理，总共 {len(folders)} 个任务")

    # ✨ 并发数量 = CPU 核心数 × 4
    max_workers = os.cpu_count() / 2
    print(f"🔥 使用并发线程数: {max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_folder, folder, api_key): folder for folder in folders}

        for future in as_completed(futures):
            print(future.result())




def main():
    with open(config_path, "r", encoding="utf-8") as f:
        api_key = json.load(f).get("API_KEY")

    if not api_key:
        print("❌ API_KEY 未在 config.json 里")
        return

    print("🔑 API Key Loaded")

    generate_results(api_key)


if __name__ == "__main__":
    main()
