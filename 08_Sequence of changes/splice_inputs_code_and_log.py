import os
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
base_dir = os.path.join(parent_dir, "output_mbppplus_new")

# ==========================================
# 在这里切换你要处理的类型
# 可选值: "original", "equivalent", "non_equivalent"
# ==========================================
type_name = "original"

# 根据需求配置不同类型的提取规则
type_configs = {
    "original": {
        "source_file": "sample_inputs.py",
        "tail_start": -12,
        "tail_end": -8
    },
    "equivalent": {
        "source_file": "sample_inputs_equivalent.py",
        "tail_start": -8,
        "tail_end": -4
    },
    "non_equivalent": {
        "source_file": "sample_inputs_non_equivalent.py",
        "tail_start": -13,
        "tail_end": -9
    }
}

# 获取当前类型的配置参数
config = type_configs.get(type_name)
if not config:
    print(f"❌ 未知的 type_name: {type_name}")
    exit(1)

# 检查 base_dir 是否存在
if not os.path.exists(base_dir):
    print(f"❌ 基础目录不存在: {base_dir}")
    exit(1)

for folder in os.listdir(base_dir):
    subdir = os.path.join(base_dir, folder)

    if not os.path.isdir(subdir) or not folder.startswith("task_"):
        continue

    # 1. 确定源文件路径
    source_file_path = os.path.join(subdir, config["source_file"])
    if not os.path.exists(source_file_path):
        print(f"⏭ 跳过 {folder}: 缺少源文件 '{config['source_file']}'")
        print(f"   📂 期望路径: {source_file_path}")
        print(f"   📋 目录 '{folder}' 中现有文件: {os.listdir(subdir) or '（空目录）'}")
        continue

    # 2. 读取源文件内容
    with open(source_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        content = "".join(lines)

    # 3. 提取 code_content
    match = re.search(r'^[ \t]*inputs\s*=', content, flags=re.MULTILINE)
    if match:
        code_content = content[:match.start()]
    else:
        print(f"⚠️ 警告: {folder} 未找到 'inputs =' 变量定义，将使用源文件全部内容作为 code_content")
        print(f"   📂 源文件路径: {source_file_path}")
        code_content = content

    # 4. 提取文件末尾的执行逻辑
    tail_start = config["tail_start"]
    tail_end = config["tail_end"]

    if len(lines) >= abs(tail_start):
        loop_lines = lines[tail_start:tail_end]
    else:
        print(f"⚠️ 警告: {folder} 源文件行数不足（共 {len(lines)} 行），无法截取倒数 {abs(tail_start)} 行")
        print(f"   📂 源文件路径: {source_file_path}")
        loop_lines = []

    # 5. 定义复用的生成逻辑：读取 txt 写入新 py
    def generate_script(status):
        input_txt_path = os.path.join(subdir, f"{type_name}_{status}_inputs.txt")
        output_py_path = os.path.join(subdir, f"sample_{type_name}_{status}.py")

        inputs = []
        if os.path.exists(input_txt_path):
            with open(input_txt_path, "r", encoding="utf-8") as f:
                inputs = [line.strip() for line in f if line.strip()]
        else:
            print(f"⏭ 跳过生成 '{os.path.basename(output_py_path)}': 缺少输入文件 '{type_name}_{status}_inputs.txt'")
            print(f"   📂 期望路径: {input_txt_path}")
            print(f"   📋 目录 '{folder}' 中现有文件: {os.listdir(subdir) or '（空目录）'}")
            return

        with open(output_py_path, "w", encoding="utf-8") as f:
            f.write(code_content)
            f.write("inputs = [\n")
            for item in inputs:
                f.write(f"    {item}\n")
            f.write("]\n\n")
            f.writelines(loop_lines)

        print(f"✅ 已生成: {os.path.basename(output_py_path)}")

    # 6. 分别为 correct 和 error 生成对应的执行脚本
    generate_script("correct")
    generate_script("error")

print("\n🎉 全部处理完成！")