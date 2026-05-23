import os

# 路径与原脚本保持一致
current_dir = os.path.dirname(os.path.abspath(__file__))
# output_path = os.path.join(current_dir, "sample_output_LLMs_original_code", "minimax")
output_path = os.path.join(current_dir, "non_equivalent_llm", "error")
"""
遍历llm输出文件，删除错误的文件
"""

def clean_error_files():
    if not os.path.exists(output_path):
        print("⚠️ 输出目录不存在")
        return

    files = os.listdir(output_path)
    print(f"🔍 开始检查 {len(files)} 个文件")

    deleted_count = 0

    for file in files:
        file_path = os.path.join(output_path, file)

        # 只处理 .txt 文件
        if not os.path.isfile(file_path) or not file.endswith(".txt"):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if content == "ERROR: empty":
                os.remove(file_path)
                print(f"🗑 删除: {file}")
                deleted_count += 1

        except Exception as e:
            print(f"⚠️ 读取失败 {file}: {e}")

    print(f"✅ 清理完成，共删除 {deleted_count} 个文件")


if __name__ == "__main__":
    clean_error_files()