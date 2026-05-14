import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI, APITimeoutError
from httpx import ReadTimeout, ConnectError, HTTPStatusError

API_BASE_URL = "https://api3.wlai.vip/v1"
NVIDA_URL = "https://integrate.api.nvidia.com/v1"

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "config.json")
output_path = os.path.join(current_dir, "non_equivalent_transform_new")
input_dir = os.path.join(current_dir, "output_mbppplus_new")
model_name = "gpt-5.1"
"""
非等价变异

"""
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
def call_llm(prompt, folder, max_retries=5):
    messages = [
        {"role": "system", "content": "Return ONLY the modified code, no explanation, no reasoning."},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                timeout=240
            )

            if not response or not hasattr(response, "choices") or not response.choices:
                print(f"⚠️ {folder} 无效响应 attempt={attempt + 1}，重试...")
                time.sleep(1)
                continue

            content = response.choices[0].message.content
            if not content.strip():
                print(f"⚠️ {folder} 空内容 attempt={attempt + 1}，重试...")
                time.sleep(1)
                continue

            return content

        except (APITimeoutError, ReadTimeout):
            print(f"⏳ {folder} Timeout attempt={attempt + 1}，重试...")
        except (HTTPStatusError, ConnectError, Exception) as e:
            print(f"⚠️ {folder} Error attempt={attempt + 1}: {e}")

        time.sleep(1)

    print(f"❌ {folder} 连续失败，返回 None")
    return None


# ================================
#   提取 ```result ... ```
# ================================
def extract_result_block(text):
    if not text:
        return "ERROR: LLM returned no result"

    pattern = r"<result>(.*?)</result>"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return text.strip()


# ================================
#   处理单个文件夹（用于并发）
# ================================
def process_folder(folder):
    # ✨ 新增：提前定义最终要保存的目标文件路径
    save_file = os.path.join(output_path, f"{folder}.py")

    # ✨ 新增：检查目标文件是否已经存在，若存在则直接跳过，避免重复处理
    if os.path.exists(save_file):
        return f"⏭ 目标文件已存在，跳过 {folder}"

    sub_dir = os.path.join(input_dir, folder)

    # if folder.startswith("task_"):
    #     try:
    #         num = int(folder.split("_")[1])
    #         if num not in  [794,748,725]:
    #             return f"⏭ 跳过 {folder}"
    #     except:
    #         pass

    if not os.path.isdir(sub_dir):
        return f"⏭ 跳过（非文件夹）: {folder}"

    combined_file = os.path.join(sub_dir, "code.py")
    if not os.path.exists(combined_file):
        return f"⚠️ {combined_file} 不存在"

    with open(combined_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    # =======================================================
    #  🔥 非等价扰动提示词 (Non-Equivalent Transformation)
    # =======================================================
    prompt = f"""
    Below is the Python code:
    {code_content}

    You are a Mutation Testing Engineer. Your goal is to introduce a single, subtle logical change that alters the correct answer of the problem.

    Mutation Rules (Pick exactly ONE):
    
    1.Relational Operator Replacement (ROR): Flip a comparison (e.g., > to <, or == to !=).
    
    2.Logical Connector Replacement (LCR): Swap logical gates (e.g., AND to OR).
    
    3.Arithmetic Operator Replacement (AOR): Change an operator (e.g., + to -, or * to /).
    
    4.Constant Value Mutation (CVM): Change a critical threshold or constant by a minimal margin (e.g., limit = 10 to limit = 11).
    
    Requirements:
    
    Minimalism: Change exactly one token or operator. The rest of the text must remain identical.
    
    Semantic Shift: Ensure the original correct solution is now incorrect for this new version.

    Output ONLY the transformed code, wrapped exactly as:

    <result> <your_transformed_code_here> </result>
    """

    print(f"🧠 调用模型 (Non-Equivalent): {folder} ...")
    llm_output = call_llm(prompt, folder)

    final_result = extract_result_block(llm_output)

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

    max_workers = os.cpu_count() // 2
    # max_workers = 1
    print(f"🔥 使用并发线程数: {max_workers}")

    print(f"🚀 开始并发处理（非等价扰动），总共 {len(folders)} 个任务")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
    init_client(api_key)

    generate_results(api_key)


if __name__ == "__main__":
    main()