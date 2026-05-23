import os

original_dir = "sample_output_LLMs_original_code/minimax"
equivalent_dir = "sample_output_LLMs_equivalent_code/minimax"
non_equivalent_dir = "sample_output_LLMs_non_equivalent_code/minimax"

def get_one_line_files(dir_path):
    """
    遍历指定目录，返回内容只有 1 行的文件名列表
    """
    one_line_files = []

    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"⚠️ [警告] 目录不存在: {dir_path}")
        return one_line_files

    for fname in os.listdir(dir_path):
        # 仅处理以 task_ 开头且以 .txt 结尾的文件
        if not fname.startswith("task_") or not fname.endswith(".txt"):
            continue

        file_path = os.path.join(dir_path, fname)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # 读取所有行，并去掉每行末尾的换行符
                lines = [line.rstrip("\n") for line in f]

                # 如果严格只有 1 行，则记录下来
                if len(lines) == 1:
                    one_line_files.append(fname)
        except Exception as e:
            print(f"❌ 读取文件 {fname} 时发生错误: {e}")

    return one_line_files


def main():
    # 将需要统计的文件夹整理成字典，方便遍历打印
    directories = {
        "Original": original_dir,
        "Equivalent": equivalent_dir,
        "Non-Equivalent": non_equivalent_dir
    }

    print("🚀 开始统计单行文件...")

    for label, path in directories.items():
        print(f"\n{"=" * 10} 【{label}】目录 {"=" * 10}")

        files_list = get_one_line_files(path)
        count = len(files_list)

        print(f"📂 只有 1 行内容的文件数量: {count}")
        if count > 0:
            print(f"📜 文件列表: {files_list}")
            # 如果希望列表打印得更好看一点（每行打印一个文件），可以使用下面的代码替换上一行：
            # print("📜 文件列表:")
            # for f in files_list:
            #     print(f"  - {f}")
        else:
            print("📜 文件列表: 无")

    print("\n✅ 统计完成！")


if __name__ == "__main__":
    main()