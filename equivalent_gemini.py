import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI, APITimeoutError
from httpx import ReadTimeout, ConnectError, HTTPStatusError

API_BASE_URL = "https://api3.wlai.vip/v1"

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
output_path = os.path.join(current_dir, "equivalent_transform", "gemini")
input_dir = os.path.join(current_dir, "output_mbppplus")
model_name = "gemini-3-pro-preview"

# ===========================
# 1. 全局 Client（只创建一次）
# ===========================
client = None

def init_client(api_key):
    global client
    if client is None:
        client = OpenAI(api_key=api_key, base_url=API_BASE_URL)


# ===============================
#  调用 LLM（复用 Client + 重试）
# ===============================
def call_llm(prompt, max_retries=5):
    messages = [
        {"role": "system", "content": "Return ONLY the final result, no explanation, no reasoning."},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                # max_tokens=200,
                timeout=240
            )

            if not response or not hasattr(response, "choices") or not response.choices:
                print(f"⚠️ 无效响应 attempt={attempt+1}，重试...")
                time.sleep(1)
                continue

            content = response.choices[0].message.content
            if not content.strip():
                print(f"⚠️ 空内容 attempt={attempt+1}，重试...")
                time.sleep(1)
                continue

            return content

        except (APITimeoutError, ReadTimeout):
            print(f"⏳ Timeout attempt={attempt+1}，重试...")
        except (HTTPStatusError, ConnectError, Exception) as e:
            print(f"⚠️ Error attempt={attempt+1}: {e}")

        time.sleep(1)

    print("❌ 连续失败，返回 None")
    return None


# ================================
#   提取 ```result ... ```
# ================================
def extract_result_block(text):
    if not text:
        return "ERROR: LLM returned no result"

    pattern = r"```result\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return text.strip()


# ================================
#   处理单个文件夹（用于并发）
# ================================
def process_folder(folder):
    sub_dir = os.path.join(input_dir, folder)

    # 跳过不需要处理的文件夹
    if any(skip in folder for skip in ["_1", "_20", "_21", "_22","_23","_24"]):
        return f"⏭ 跳过 {folder}"

    if not os.path.isdir(sub_dir):
        return f"⏭ 跳过（非文件夹）: {folder}"

    combined_file = os.path.join(sub_dir, "combined.py")
    if not os.path.exists(combined_file):
        return f"⚠️ {combined_file} 不存在"

    with open(combined_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    prompt = (
        f"Below is the Python code:\n\n```python\n{code_content}\n```\n\n"
        f"Please output ONLY the final result.\n"
        f"Wrap it exactly as:\n\n"
        f"```result\n<your_output_here>\n```\n"
    )

    print(f"🧠 调用模型: {folder} ...")
    llm_output = call_llm(prompt)

    final_result = extract_result_block(llm_output)

    save_file = os.path.join(output_path, f"{folder}.txt")
    with open(save_file, "w", encoding="utf-8") as f:
        f.write(final_result)

    return f"✅ 完成：{folder}"


# ================================
#   主并发调度
# ================================
def generate_results(api_key):
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)

    folders = [f for f in os.listdir(input_dir)]

    print(f"🚀 开始并发处理，总共 {len(folders)} 个任务")

    # 使用 5 并发线程
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_folder, folder): folder for folder in folders}

        for future in as_completed(futures):
            print(future.result())


def main():
    with open(config_path, "r", encoding="utf-8") as f:
        api_key = json.load(f).get("API_KEY")

    if not api_key:
        print("❌ API_KEY 未在 config.json 中找到!")
        return

    print("🔑 API Key Loaded")
    init_client(api_key)    # 初始化全局 client

    generate_results(api_key)


if __name__ == "__main__":
    main()
