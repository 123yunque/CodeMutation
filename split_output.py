import os

original_dir = "sample_output_LLMs_original_code/minimax"
equivalent_dir = "sample_output_LLMs_equivalent_code/minimax"
non_equivalent_dir = "sample_output_LLMs_non_equivalent_code/minimax"


def process_and_split_one_line_files(dir_path):
    """
    遍历指定目录，找到只有 1 行内容的文件，
    将其按空格分隔后，每个元素占一行，覆盖写回原文件。
    """
    modified_files = []

    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"⚠️ [警告] 目录不存在: {dir_path}")
        return modified_files

    for fname in os.listdir(dir_path):
        # 仅处理以 task_ 开头且以 .txt 结尾的文件
        if not fname.startswith("task_") or not fname.endswith(".txt"):
            continue

        file_path = os.path.join(dir_path, fname)

        try:
            # 1. 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f]

            # 2. 检查是否严格只有 1 行，且该行不是纯空白
            if len(lines) == 1 and lines[0].strip():
                single_line = lines[0]

                # 将单行字符串按空格（支持多个连续空格）进行分隔
                elements = single_line.split()

                # 3. 覆盖写入原文件，每个元素一行
                with open(file_path, "w", encoding="utf-8") as f:
                    for item in elements:
                        f.write(item + "\n")

                modified_files.append(fname)

        except Exception as e:
            print(f"❌ 处理文件 {fname} 时发生错误: {e}")

    return modified_files


def main():
    # 将需要统计的文件夹整理成字典，方便遍历打印
    directories = {
        "Original": original_dir,
        "Equivalent": equivalent_dir,
        "Non-Equivalent": non_equivalent_dir
    }

    print("🚀 开始扫描并转换单行文件...")

    for label, path in directories.items():
        print(f"\n{'=' * 10} 【{label}】目录 {'=' * 10}")

        # 执行转换并获取被修改的文件列表
        modified_list = process_and_split_one_line_files(path)
        count = len(modified_list)

        print(f"📂 成功分隔并重写了 {count} 个文件")
        if count > 0:
            print(f"📜 被修改的文件列表: {modified_list}")
        else:
            print("📜 没有需要处理的单行文件。")

    print("\n✅ 所有目录格式化完成！")


if __name__ == "__main__":
    main()