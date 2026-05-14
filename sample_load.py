import os
import json
import re
import random
from itertools import cycle

from datasets import load_dataset
"""
加载数据集---随机保留10个测试用例
"""
# 加载数据集（这里使用 evalplus/mbppplus）
ds = load_dataset("evalplus/mbppplus")["test"]
output_model = "model.py"
# 输出主目录
output_dir = "output_mbppplus_new"
os.makedirs(output_dir, exist_ok=True)


def process_test_field(test_str):
    """
    去掉 test 中 'inputs' 之前的部分，并删除 'assertion(...内容...)' 及其后的部分
    """

    def remove_assertion(line):
        if "assertion" in line:
            line = line.split(")")[0] + ")"
        return line

    keyword = "inputs"
    idx = test_str.find(keyword)
    if idx != -1:
        test_str = "\n".join([remove_assertion(line) for line in test_str[idx:].splitlines()])
        return test_str
    else:
        return "\n".join([remove_assertion(line) for line in test_str.splitlines()])


def save_item(item):
    task_id = int(item["task_id"])

    # 如果 task_id 小于 226，则直接跳过
    if task_id < 226:
        print(f"⏭ 跳过任务: task_{task_id} (ID < 226)")
        return

    # 创建任务文件夹
    folder_path = os.path.join(output_dir, f"task_{task_id}")
    if os.path.exists(folder_path):
        print(f"⚠️ 文件夹已存在，将覆盖其内部文件: {folder_path}")
    os.makedirs(folder_path, exist_ok=True)

    # 各个生成文件的路径
    json_path = os.path.join(folder_path, f"task_{task_id}.json")
    combined_path = os.path.join(folder_path, "combined.py")
    results_path = os.path.join(folder_path, "results.txt")
    code_path = os.path.join(folder_path, "code.py")
    inputs_path = os.path.join(folder_path, "code_inputs.txt")
    sample_inputs_path = os.path.join(folder_path, "sample_code_inputs.txt")

    # 保存 JSON 文件 ("w" 模式会自动覆盖)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=4)

    # 处理 test
    test_processed = ""
    if isinstance(item.get("test"), str):
        test_processed = process_test_field(item["test"])
    elif isinstance(item.get("test"), list):
        test_processed = "\n".join([process_test_field(t) for t in item["test"]])

    # ================= 解析并存储 inputs =================
    inputs_match = re.search(r"inputs\s*=\s*(\[.*?\])\s*\nresults", test_processed, re.DOTALL)
    if inputs_match:
        inputs_str = inputs_match.group(1)
        try:
            # 将字符串解析为 Python 列表，注入 inf 处理极端数值
            inputs_list = eval(inputs_str, {"__builtins__": {}}, {"inf": float('inf')})

            # 1. 保存所有输入到 code_inputs.txt
            with open(inputs_path, "w", encoding="utf-8") as f:
                for inp in inputs_list:
                    f.write(json.dumps(inp, ensure_ascii=False) + "\n")

            # 2. 随机保留 10 行到 sample_code_inputs.txt
            with open(sample_inputs_path, "w", encoding="utf-8") as f:
                sample_size = min(10, len(inputs_list))
                sampled_inputs = random.sample(inputs_list, sample_size)
                for inp in sampled_inputs:
                    f.write(json.dumps(inp, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Warning: Failed to parse inputs for task {task_id}: {e}")
    # ===============================================================

    # 分离 results 开头的行与拼装 combined.py
    combined_lines = []
    results_lines = []
    cycle_head = "result = []\nfor inp in inputs:"

    output_path = """
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
inputs_file = os.path.join(current_dir, 'code_inputs.txt')
results_file = os.path.join(current_dir, 'code_results.txt')
"""
    combined_lines.append(output_path)

    for line in test_processed.splitlines():
        if line.strip().startswith("results"):
            results_lines.append(line[10:])
        elif line.strip().startswith("for"):
            combined_lines.append(cycle_head)
        elif line.strip().startswith("assertion"):
            combined_lines.append("    result.append(" + line[14:] + ")")
        else:
            combined_lines.append(line)

    # code 内容
    code_content = item.get("code", "")

    # 尝试加载 model.py
    model_content = ""
    if os.path.exists(output_model):
        with open(output_model, "r", encoding="utf-8") as mf:
            model_content = mf.read()
    combined_lines.append(model_content)

    # 写入 combined.py ("w" 模式会自动覆盖)
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(code_content + "\n")
        f.write("\n".join(combined_lines) + "\n")

    # 写入 code.py ("w" 模式会自动覆盖)
    with open(code_path, "w", encoding="utf-8") as rf:
        rf.write(code_content + "\n")

    # 写入 results.txt（如果存在）("w" 模式会自动覆盖)
    if results_lines:
        with open(results_path, "w", encoding="utf-8") as f:
            f.write("\n".join(results_lines))

    print(f"✅ Saved task folder: {folder_path} (Included inputs extraction & overwrite)")


print("Total tasks:", len(ds))

for item in ds:
    save_item(item)
    # break

print("All tasks saved with combined.py, results.txt, and inputs files. Existing files were overwritten.")