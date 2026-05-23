import os
from pathlib import Path

TARGET_DIR = "output_mbppplus_new"
TARGET_FILE = "sample_original_correct.py"


def clean_pragmas():
    target_path = Path(TARGET_DIR)
    py_files = list(target_path.rglob(TARGET_FILE))

    print(f"🔍 准备清洗 {len(py_files)} 个文件...")
    cleaned_count = 0

    for py_file in py_files:
        with open(py_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 检查第一行是否包含禁止插桩的指令
        if lines and "DYNAPYT: DO NOT INSTRUMENT" in lines[0]:
            # 删掉这一行
            lines.pop(0)

            # 写回文件
            with open(py_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            cleaned_count += 1

    print(f"✅ 清洗完成！共拔除了 {cleaned_count} 个文件中的禁止插桩指令。")


if __name__ == "__main__":
    clean_pragmas()