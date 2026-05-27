import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from paths import ROOT, MBPP_DIR

import os

base_dir = str(MBPP_DIR)

base_output_path = """
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
inputs_file = os.path.join(current_dir, 'sample_code_inputs.txt')
results_file = os.path.join(current_dir, 'sample_code_results.txt')
"""

# ✨ 新增：在外层提前读取目录下的 model.py
model_path = os.path.join(os.path.dirname(__file__), "model.py")
model_content = ""
if os.path.exists(model_path):
    with open(model_path, "r", encoding="utf-8") as f:
        model_content = f.read()
    print("✅ 成功加载同级目录下的 model.py\n")
else:
    print("⚠️ 警告：当前目录下未找到 model.py，后续将不会追加模型内容。\n")

for folder in os.listdir(base_dir):
    subdir = os.path.join(base_dir, folder)
    if not os.path.isdir(subdir):
        continue

    code_path = os.path.join(subdir, "code.py")
    combined_path = os.path.join(subdir, "combined.py")
    input_txt_path = os.path.join(subdir, "sample_code_inputs.txt")
    output_path = os.path.join(subdir, "sample_inputs.py")

    inputs = []

    # 如果缺少核心文件则跳过
    if not os.path.exists(code_path) or not os.path.exists(combined_path):
        print(f"跳过 {subdir} （缺少 code.py 或 combined.py）")
        continue

    # 读取 sample_code_inputs.txt，逐行加入 inputs 数组
    if os.path.exists(input_txt_path):
        with open(input_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    inputs.append(line)
    else:
        print(f"提示：{subdir} 下没有 sample_code_inputs.txt，inputs 将为空数组")

    # 读取 code.py
    with open(code_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    # 读取 combined.py 的最后 11 行
    with open(combined_path, "r", encoding="utf-8") as f:
        combined_lines = f.readlines()
        last_11_lines = combined_lines[-11:-8]

    # 合并写入新的文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code_content)
        f.write("\n\ninputs = [\n")
        for item in inputs:
            f.write(f"    {item},\n")
        f.write("]\n\n")
        f.write(base_output_path)
        f.writelines(last_11_lines)

        #✨ 追加提取好的 model.py 内容
        if model_content:
            f.write("\n")  # 换行，确保与上一段代码隔开
            f.write(model_content)

    print(f"已生成: {output_path}")