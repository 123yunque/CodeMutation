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

import os

original_dir = str(LLM_ORIGINAL / "gpt51")
mbpp_dir = str(MBPP_DIR)
equivalent_dir = str(LLM_EQUIV / "gpt51")
non_equivalent_dir = str(LLM_NON_EQUIV / "gpt51")
"""
对比本地输出结果以及LLM输出结果，上面dir部分修改模型目录
"""

def read_lines(path):
    """读取文件所有行，保留中间空格，只去掉换行符"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def calculate_LLM_and_local(file_path):
    results = []  # 保存每个 task 的对比结果
    total_same_lines = 0
    total_original_lines = 0

    full_same_tasks = 0
    partial_same_tasks = 0
    all_diff_tasks = 0

    # 输入文件路径
    original_inputs = "sample_code_inputs.txt"

    # 根据类型选择对应保存路径
    if "original" in file_path:
        file_type = "original"
        result_path = original_dir
        sample_code_name = "sample_code_results.txt"
        fileter_correct_inputs_name = "original_correct_inputs.txt"
        fileter_error_inputs_name = "original_error_inputs.txt"
    elif "non_equivalent" in file_path:
        file_type = "non_equivalent"
        result_path = non_equivalent_dir
        sample_code_name = "sample_code_results_non_equivalent.txt"
        fileter_correct_inputs_name = "non_equivalent_correct_inputs.txt"
        fileter_error_inputs_name = "non_equivalent_error_inputs.txt"
    else:
        file_type = "equivalent"
        result_path = equivalent_dir
        sample_code_name = "sample_code_results_equivalent.txt"
        fileter_correct_inputs_name = "equivalent_correct_inputs.txt"
        fileter_error_inputs_name = "equivalent_error_inputs.txt"

    # 读取 original_inputs
    for fname in os.listdir(file_path):
        if not fname.startswith("task_") or not fname.endswith(".txt"):
            continue
        num = int(fname.split("_")[1][:-4])
        # if num > 224:
        #     continue
        task_id = fname[:-4]
        code_result_path = os.path.join(result_path, fname)
        sample_code_path = os.path.join(mbpp_dir, task_id, sample_code_name)
        original_inputs_dir = os.path.join(mbpp_dir,task_id, original_inputs)
        input_lines = read_lines(original_inputs_dir)
        if input_lines is None:
            print(f"[错误] 无法读取 {original_inputs}")
            return
        if not os.path.exists(sample_code_path):
            print(f"[缺失] {task_id} 下没有 {sample_code_name}")
            continue

        original_lines = read_lines(code_result_path)
        sample_lines = read_lines(sample_code_path)
        if original_lines is None or sample_lines is None:
            print(f"[错误] 无法读取文件: {task_id}")
            continue

        # 过滤掉无效行
        filtered_pairs = [
            (a, b)
            for a, b in zip(original_lines, sample_lines)
            if b != "变异前后结果相同，认为该测试用例无效"
        ]

        # ------ ★ 新增功能：处理第一行相同 和 第一行不同 ★ ------
        first_same_written = False
        first_diff_written = False

        correct_dir = os.path.join(mbpp_dir, task_id, fileter_correct_inputs_name)
        error_dir = os.path.join(mbpp_dir, task_id, fileter_error_inputs_name)

        # ★ 新增：提前清理历史残留文件
        if os.path.exists(correct_dir): os.remove(correct_dir)
        if os.path.exists(error_dir): os.remove(error_dir)
        for idx, (a, b) in enumerate(filtered_pairs):
            input_line = input_lines[idx] if idx < len(input_lines) else ""

            if a == b and not first_same_written:
                with open(correct_dir, "w", encoding="utf-8") as f:
                    f.write(f"{input_line}\n")
                first_same_written = True

            if a != b and not first_diff_written:
                with open(error_dir, "w", encoding="utf-8") as f:
                    f.write(f"{input_line}\n")
                first_diff_written = True

            if first_same_written and first_diff_written:
                break
        # --------------------------------------------------------

        # 行级对比
        diff_line_numbers = [idx + 1 for idx, (a, b) in enumerate(filtered_pairs) if a != b]
        same_line_count = sum(1 for a, b in filtered_pairs if a == b)

        total_same_lines += same_line_count
        total_original_lines += len(filtered_pairs)

        # 代码级统计
        if same_line_count == len(filtered_pairs):
            full_same_tasks += 1
        elif same_line_count == 0:
            all_diff_tasks += 1
        else:
            partial_same_tasks += 1
        results.append((task_id, same_line_count, len(filtered_pairs), len(sample_lines), diff_line_numbers))
    # 输出统计
    print("\n===== 每个代码对比结果 =====")
    for task_id, same_cnt, orig_total, sample_total, diff_lines in results:
        print(f"{task_id}: 相同的测试用例数 = {same_cnt} / 测试用例数 {orig_total}")
        print(f"    不同测试用例的行号: {diff_lines}")

    overall_ratio = (total_same_lines / total_original_lines) if total_original_lines > 0 else 0

    print("\n===== 总体统计 =====")
    print(f"{file_type}模型回答结果与本地执行结果相同测试用例数: {total_same_lines}")
    print(f"{file_type}总测试用例数: {total_original_lines}")
    print(f"{file_type}整体测试用例正确率: {overall_ratio:.2%}")

    print(f"\n📌 完全正确的代码数量: {full_same_tasks}")
    print(f"📌 部分正确的代码数量: {partial_same_tasks}")
    print(f"📌 完全错误的代码数量: {all_diff_tasks}")

    print("\n===== 完成 =====")


def calculate_LLMs(file_path1, file_path2):
    results = []
    total_same_lines = 0
    total_original_lines = 0

    full_same_tasks = 0
    partial_same_tasks = 0
    all_diff_tasks = 0

    for fname in os.listdir(file_path1):
        if not fname.startswith("task_") or not fname.endswith(".txt"):
            continue

        task_id = fname[:-4]
        code_result_path = os.path.join(file_path1, fname)
        sample_code_path = os.path.join(file_path2, fname)

        original_lines = read_lines(code_result_path)
        sample_lines = read_lines(sample_code_path)

        if original_lines is None or sample_lines is None:
            print(f"[错误] 无法读取文件: {task_id}")
            continue

        diff_line_numbers = [
            idx + 1 for idx, (a, b) in enumerate(zip(original_lines, sample_lines)) if a != b
        ]

        same_line_count = sum(1 for a, b in zip(original_lines, sample_lines) if a == b)
        total_same_lines += same_line_count
        total_original_lines += len(original_lines)

        if same_line_count == len(original_lines):
            full_same_tasks += 1
        elif same_line_count == 0:
            all_diff_tasks += 1
        else:
            partial_same_tasks += 1

        results.append((task_id, same_line_count, len(original_lines), len(sample_lines), diff_line_numbers))

    print("\n===== 每个代码对比结果 =====")
    for task_id, same_cnt, orig_total, sample_total, diff_lines in results:
        print(f"{task_id}: 相同的行数 = {same_cnt} / 测试用例数 {sample_total}")
        print(f"    不同行的行号: {diff_lines}")

    overall_ratio = (total_same_lines / total_original_lines) if total_original_lines > 0 else 0

    print("\n===== 总体统计 =====")
    print(f"代码总相同行数: {total_same_lines}")
    print(f"总 original 行数: {total_original_lines}")
    print(f"整体相似度: {overall_ratio:.2%}")

    print(f"\n📌 完全相同的代码数量: {full_same_tasks}")
    print(f"📌 部分相同的代码数量: {partial_same_tasks}")
    print(f"📌 完全不同的代码数量: {all_diff_tasks}")

    print("\n===== 完成 =====")


def main():
    calculate_LLM_and_local(original_dir)
    calculate_LLM_and_local(equivalent_dir)
    calculate_LLM_and_local(non_equivalent_dir)
    # calculate_LLMs(original_dir, non_equivalent_dir)


if __name__ == "__main__":
    main()
