# [auto-patched by patch_imports.py]
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from paths import (
    ROOT, CONFIG, CONFIG1, MBPP_DIR,
    EQUIV_TRANSFORM, NON_EQUIV_TRANSFORM,
    LLM_ORIGINAL, LLM_EQUIV, LLM_NON_EQUIV,
    LOCAL_ORIGINAL, LOCAL_EQUIV, LOCAL_NON_EQUIV,
    LLM_TRACE_ORIGINAL, LLM_TRACE_EQUIV, LLM_TRACE_NON_EQUIV,
)

import json
import os

base_dir = str(MBPP_DIR)
fun_dir = str(EQUIV_TRANSFORM)

base_output_path = r"""
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
results_file = os.path.join(current_dir, 'sample_code_results_equivalent.txt')

result = []
for inp in inputs:
    result.append(fun1(*inp))
# 写 results，每项一行
with open(results_file, 'w', encoding='utf-8') as f:
    for item in result:
        f.write(str(item) + "\n")
"""


def parse_input_lines(path):
    parsed_inputs = []
    if not os.path.exists(path):
        return parsed_inputs

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parsed_inputs.append(json.loads(line))
            except json.JSONDecodeError:
                parsed_inputs.append(line)
    return parsed_inputs

for folder in os.listdir(base_dir):
    subdir = os.path.join(base_dir, folder)

    fun_name = folder+".py"

    if not os.path.isdir(subdir):
        continue

    code_path = os.path.join(fun_dir, fun_name)
    combined_path = os.path.join(subdir, "combined.py")
    input_txt_path = os.path.join(subdir, "sample_code_inputs.txt")
    output_path = os.path.join(subdir, "sample_inputs_equivalent.py")

    inputs = []

    # 如果缺少文件则跳过
    # if folder.startswith("task_"):
    #     try:
    #         num = int(folder.split("_")[1])
    #         if num > 226:
    #             continue
    #     except:
    #         pass

    # 读取 code_inputs.txt，逐行加入 inputs 数组
    if os.path.exists(input_txt_path):
        inputs = parse_input_lines(input_txt_path)
    else:
        print(f"提示：{subdir} 下没有 code_inputs.txt，inputs 将为空数组")

    # 读取 code.py
    with open(code_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    # 读取 combined.py 的最后 11 行
    # with open(combined_path, "r", encoding="utf-8") as f:
    #     combined_lines = f.readlines()
    #     last_11_lines = combined_lines[-11:-8]

    # 合并写入新的文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code_content)
        f.write("\n\ninputs = [\n")
        for item in inputs:
            f.write(f"    {repr(item)},\n")
        f.write("]\n\n")
        f.write(base_output_path)
        # f.writelines(last_11_lines)

    print(f"已生成: {output_path}")
