import threading
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI, APITimeoutError
from httpx import ReadTimeout, ConnectError, HTTPStatusError
# 线程安全的 OpenAI 客户端

"""
run_tasks.py 用到的工具 👇base_url写api的地址 config1.json里定义好apikey
"""
thread_local = threading.local()
def get_client(api_key=os.getenv("NVIDIA_API_KEY"), base_url="https://integrate.api.nvidia.com/v1"):
    """生成线程安全的 OpenAI 客户端"""
    if not hasattr(thread_local, "client"):
        thread_local.client = OpenAI(api_key=api_key, base_url=base_url)
    return thread_local.client
def call_llm(prompt, folder, api_key, model_name, max_retries=5):
    """调用 LLM，支持指数退避重试机制"""
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
            print(f"⚠️ {folder} 空内容 attempt={attempt + 1}")
        except (APITimeoutError, ReadTimeout):
            print(f"⏳ Timeout during {folder}, attempt={attempt + 1}")
        except (ConnectError, HTTPStatusError, Exception) as e:
            print(f"⚠️ Error {folder}: {e} attempt={attempt + 1}")
        time.sleep(2 ** attempt)  # Exponential backoff
    print(f"❌ {folder} 连续失败")
    return None
def extract_result_block(text):
    """提取结果块"""
    if not text:
        return "ERROR: empty"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()
def process_folder(folder, input_dir, output_path, api_key, model_name, input_file_name):
    """处理特定文件夹中的任务"""
    save_file = os.path.join(output_path, f"{folder}.txt")
    if os.path.exists(save_file):
        return f"⏭️ 文件已存在，跳过 {folder}"
    sub_dir = os.path.join(input_dir, folder)
    if not os.path.isdir(sub_dir):
        return f"⏭️ 非文件夹 {folder}"
    combined_file = os.path.join(sub_dir, input_file_name)
    if not os.path.exists(combined_file):
        return f"⚠️ {combined_file} 不存在: {folder}"
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

        Rules:
        1. If the code produces no output, you must still return one empty line between <result> tags.
        2. Do NOT include any explanations, debug info, or extra text.
        3. Only return results in the <result> ... </result> block.

        Example:
        If there are results:
        <result>
        3
        7
        </result>

        If there are no results:
        <result>

        </result>

        Now execute the code and return results ONLY in:
        <result> ... </result>
        """

    llm_output = call_llm(prompt, folder, api_key, model_name)
    final_result = extract_result_block(llm_output)
    with open(save_file, "w", encoding="utf-8") as f:
        f.write(final_result)
    return f"✅ 完成: {folder}"
def execute_task_with_threads(input_dir, output_path, api_key, model_name, input_file_name, max_workers=2):
    """使用线程池并发处理任务"""
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    folders = [f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))]
    print(f"🚀 开始并发处理，共 {len(folders)} 个任务")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = [executor.submit(process_folder, folder, input_dir, output_path, api_key, model_name, input_file_name)
                 for folder in folders]
        for future in as_completed(tasks):
            print(future.result())