import os
import re

# ================= 目标目录配置 =================
base_dirs = {
    "Equivalent Correct": "equivalent_llm/correct",
    "Equivalent Error": "equivalent_llm/error",
    "Non-Equivalent Correct": "non_equivalent_llm/correct",
    "Non-Equivalent Error": "non_equivalent_llm/error",
    "Original Correct": "original_llm/correct",
    "Original Error": "original_llm/error"
}


# ===================================================

def process_one_line_files_with_regex(dir_path):
    """
    遍历指定目录，寻找只有 1 行内容的文件。
    使用正则表达式智能分割字典格式字符串，并将结果写回文件，每项占一行。
    """
    processed_files = []

    # 检查目录是否存在
    if not os.path.exists(dir_path):
        print(f"⚠️ [警告] 目录不存在: {dir_path}")
        return processed_files

    for fname in os.listdir(dir_path):
        # 仅处理以 task_ 开头且以 .txt 结尾的文件
        if not fname.startswith("task_") or not fname.endswith(".txt"):
            continue

        file_path = os.path.join(dir_path, fname)

        # 确保它是一个文件而不是子文件夹
        if not os.path.isfile(file_path):
            continue

        try:
            # 第一步：读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f]

            # 第二步：判断是否严格只有 1 行
            if len(lines) == 1:
                original_line = lines[0]

                # 【核心修改：方案一 智能正则分割】
                # 在“空格后面紧跟单引号”的地方进行分割，完美保持列表完整性
                # 新代码：升级版智能正则，只匹配带有冒号的键
                split_items = re.split(r"\s+(?='[^']+':)", original_line.strip())

                # 第三步：将分割后的内容重新写回原文件，每项占一行
                with open(file_path, "w", encoding="utf-8") as f:
                    for item in split_items:
                        # 去除可能的首尾多余空格，保证写入整洁
                        clean_item = item.strip()
                        if clean_item:
                            f.write(clean_item + "\n")

                processed_files.append(fname)

        except Exception as e:
            print(f"❌ 处理文件 {fname} 时发生错误: {e}")

    return processed_files


def main():
    print("🚀 开始扫描并使用【智能正则方案】处理各目录下的单行文件...")

    total_processed = 0

    for label, path in base_dirs.items():
        print(f"\n{'=' * 10} 【{label}】目录 {'=' * 10}")

        # 处理并获取被修改的文件列表
        files_list = process_one_line_files_with_regex(path)
        count = len(files_list)
        total_processed += count

        print(f"📂 成功分割并重写的文件数量: {count}")
        if count > 0:
            print("📜 被处理的文件列表:")
            print(*files_list)
            # for f in files_list:
            #     print(f"  - {f}")
        else:
            print("📜 无需要处理的文件。")

    print(f"\n✅ 所有目录处理完成！共处理了 {total_processed} 个文件。")


if __name__ == "__main__":
    main()