import os
import json
import re
from itertools import cycle

from datasets import load_dataset

# 加载数据集（这里使用 evalplus/mbppplus）
ds = load_dataset("evalplus/mbppplus")["test"]

# 输出主目录
output_dir = "output_mbppplus"
os.makedirs(output_dir, exist_ok=True)

def process_test_field(test_str):
    """
    去掉 test 中 'inputs' 之前的部分，并删除 'assertion(...内容...)' 及其后的部分
    """
    # 删除 'assertion(' 及其后的所有内容，直到第一个 ')'
    def remove_assertion(line):
        # 如果行中有 assertion，删除第一个 ')' 后的内容
        if "assertion" in line:
            line = line.split(")")[0] + ")"  # 截取到第一个 ')' 为止
        return line

    # 删除 'inputs' 之前的部分
    keyword = "inputs"
    idx = test_str.find(keyword)
    if idx != -1:
        # 处理每一行，删除包含 'assertion' 的部分
        test_str = "\n".join([remove_assertion(line) for line in test_str[idx:].splitlines()])
        return test_str
    else:
        # 处理每一行，删除包含 'assertion' 的部分
        return "\n".join([remove_assertion(line) for line in test_str.splitlines()])


def save_item(item):
    task_id = item["task_id"]

    # 创建任务文件夹
    folder_path = os.path.join(output_dir, f"task_{task_id}")
    os.makedirs(folder_path, exist_ok=True)

    # 保存 JSON 文件
    json_path = os.path.join(folder_path, f"task_{task_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=4)

    # 生成 combined 文件与 results 文件
    combined_path = os.path.join(folder_path, "combined.py")
    results_path = os.path.join(folder_path, "results.txt")

    # 处理 test
    test_processed = ""
    if isinstance(item.get("test"), str):
        test_processed = process_test_field(item["test"])
    elif isinstance(item.get("test"), list):
        test_processed = "\n".join([process_test_field(t) for t in item["test"]])

    # 分离 results 开头的行
    combined_lines = []
    results_lines = []
    cycle_head = "result = []\nfor inp in inputs:"

    output_path = """
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')
"""
    combined_lines.append(output_path)

    for line in test_processed.splitlines():
        if line.strip().startswith("results"):
            results_lines.append(line[10:])
        elif line.strip().startswith("for"):
            combined_lines.append(cycle_head)
        elif line.strip().startswith("assertion"):
            combined_lines.append("    result.append("+line[14:]+")")
        else:
            combined_lines.append(line)
    push_list = "with open('code_result.txt', 'w', encoding='utf-8')"+" as f: f.write(str(result))"
    combined_lines.append(push_list)
    # code 内容
    code_content = item.get("code", "")

    # 写入 combined.py
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(code_content + "\n")
        f.write("\n".join(combined_lines) + "\n")


    # 写入 results.txt（如果存在）
    if results_lines:
        with open(results_path, "w", encoding="utf-8") as f:
            f.write("\n".join(results_lines))

    print(f"Saved task folder: {folder_path}")


print("Total tasks:", len(ds))

for item in ds:
    save_item(item)

print("All tasks saved with combined.py and results.txt files.")
