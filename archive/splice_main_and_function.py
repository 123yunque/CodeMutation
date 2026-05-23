import os

base_dir = "output_mbppplus_new"
fun_dir = "equivalent_transform_new"

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
        with open(input_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    inputs.append(line)
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
            f.write(f"    {item},\n")
        f.write("]\n\n")
        f.write(base_output_path)
        # f.writelines(last_11_lines)

    print(f"已生成: {output_path}")
