import os

original_dir = "non_equivalent_transform_new"
mbpp_dir = "output_mbppplus_new"


def read_lines(path):
    """读取文件所有行，保留中间空格，只去掉换行符"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def main():
    total_same_file = 0
    results = []  # 保存每个 task 的对比结果
    total_same_lines = 0
    total_original_lines = 0

    for fname in os.listdir(original_dir):
        # print(fname)
        # if not fname.startswith("task_") or not fname.endswith(".txt"):
        #     continue
        if not fname.startswith("task_") or not fname.endswith(".py"):
            continue

        task_id = fname[:-3]
        # original_path = os.path.join(original_dir, fname)
        sample_code_path = os.path.join(mbpp_dir, task_id, "sample_code_results.txt")
        sample_code_equivalent_path = os.path.join(mbpp_dir, task_id, "sample_code_results_non_equivalent.txt")
        if not os.path.exists(sample_code_path):
            print(f"[缺失] {task_id} 下没有 sample_code_results_non_equivalent.txt")
            continue

        original_lines = read_lines(sample_code_equivalent_path)
        sample_lines = read_lines(sample_code_path)

        if original_lines is None or sample_lines is None:
            print(f"[错误] 无法读取文件: {task_id}")
            continue

        # 行级内容对比
        same_line_count = sum(
            1 for a, b in zip(original_lines, sample_lines) if a == b
        )

        total_same_lines += same_line_count
        if same_line_count == 10 :
            total_same_file += 1
        total_original_lines += len(original_lines)

        results.append((task_id, same_line_count, len(original_lines), len(sample_lines)))

    # 输出每个任务结果
    print("\n===== 每个任务对比结果 =====")
    for task_id, same_cnt, orig_total, sample_total in results:
        print(f"{task_id}: 相同的行数 = {same_cnt} / original({orig_total}) sample({sample_total})")

    # 计算总相似度百分比
    overall_ratio = (total_same_lines / total_original_lines) if total_original_lines > 0 else 0
    print("\n===== 总体统计 =====")
    print(f"总相同行数: {total_same_lines}")
    print(f"完全相同数量：: {total_same_file}")
    print(f"总 original 行数: {total_original_lines}")
    print(f"整体相似度: {overall_ratio:.2%}")

    print("\n===== 完成 =====")





if __name__ == "__main__":
    main()
