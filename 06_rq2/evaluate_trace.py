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

# ================= 目录配置 =================
llm_dirs = {
    "Equivalent Correct": str(LLM_TRACE_EQUIV / "correct"),
    "Equivalent Error": str(LLM_TRACE_EQUIV / "error"),
    "Non-Equivalent Correct": str(LLM_TRACE_NON_EQUIV / "correct"),
    "Non-Equivalent Error": str(LLM_TRACE_NON_EQUIV / "error"),
    "Original Correct": str(LLM_TRACE_ORIGINAL / "correct"),
    "Original Error": str(LLM_TRACE_ORIGINAL / "error")
}

local_dirs = {
    "Equivalent Correct": str(LOCAL_EQUIV / "correct"),
    "Equivalent Error": str(LOCAL_EQUIV / "error"),
    "Non-Equivalent Correct": str(LOCAL_NON_EQUIV / "correct"),
    "Non-Equivalent Error": str(LOCAL_NON_EQUIV / "error"),
    "Original Correct": str(LOCAL_ORIGINAL / "correct"),
    "Original Error": str(LOCAL_ORIGINAL / "error")
}


# ============================================

def parse_file_to_dict(filepath):
    """
    读取文件，将其内容解析为字典格式 { '变量名': '变量值字符串' }
    """
    data_dict = {}
    if not os.path.exists(filepath):
        return data_dict

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 以第一个冒号进行分割
            if ":" in line:
                parts = line.split(":", 1)
                # 清理变量名，去掉两端空格以及包裹的单/双引号
                var_name = parts[0].strip().strip("'").strip('"')
                var_value = parts[1].strip()
                data_dict[var_name] = var_value

    return data_dict


def compare_directories(llm_dir, local_dir):
    """
    对比两个目录下的对应文件
    返回: (有效对比的文件数, result相同的文件数, 全变量相同的文件数, 匹配的变量总个数, 基准变量总个数, 全一致文件名列表, 仅result一致文件名列表)
    """
    if not os.path.exists(llm_dir) or not os.path.exists(local_dir):
        return 0, 0, 0, 0, 0, [], []

    llm_files = set(f for f in os.listdir(llm_dir) if f.startswith("task_") and f.endswith(".txt"))
    local_files = set(f for f in os.listdir(local_dir) if f.startswith("task_") and f.endswith(".txt"))
    common_files = llm_files.intersection(local_files)

    valid_files_count = 0
    result_match_count = 0
    all_match_count = 0

    total_vars_matched = 0
    total_vars_compared = 0

    # 新增：记录特定文件名的列表
    all_match_files = []
    result_only_match_files = []

    # 为了让输出的文件名列表有序，可以对 common_files 进行排序
    for fname in sorted(common_files):
        llm_path = os.path.join(llm_dir, fname)
        local_path = os.path.join(local_dir, fname)

        dict_llm = parse_file_to_dict(llm_path)
        dict_local = parse_file_to_dict(local_path)

        # ==========================================
        # 1. 检查是否存在 result
        # ==========================================
        if "result" not in dict_llm or "result" not in dict_local:
            continue

        valid_files_count += 1

        # 检查 result 是否相同，并记录状态
        is_result_match = (dict_llm["result"] == dict_local["result"])
        if is_result_match:
            result_match_count += 1

        # ==========================================
        # 2. 统计变量匹配的具体数量
        # ==========================================
        if len(dict_llm) <= len(dict_local):
            base_dict = dict_llm
            compare_dict = dict_local
        else:
            base_dict = dict_local
            compare_dict = dict_llm

        matched_vars_in_file = 0

        for var_name, var_value in base_dict.items():
            if var_name in compare_dict and compare_dict[var_name] == var_value:
                matched_vars_in_file += 1

        total_vars_compared += len(base_dict)
        total_vars_matched += matched_vars_in_file

        # 判断是否“所有变量都相同”
        is_all_match = (len(base_dict) > 0 and matched_vars_in_file == len(base_dict))

        # ==========================================
        # 3. 分配文件名到对应列表
        # ==========================================
        if is_all_match:
            all_match_count += 1
            all_match_files.append(fname)
        elif is_result_match:
            # 如果不是全相同，但是 result 相同，归入“仅 result 相同”列表
            result_only_match_files.append(fname)

    return valid_files_count, result_match_count, all_match_count, total_vars_matched, total_vars_compared, all_match_files, result_only_match_files


def main():
    print("🚀 开始对比 LLM 目录 与 Local 目录的文件内容...\n")

    global_files = 0
    global_result_matches = 0
    global_all_matches = 0
    global_vars_matched = 0
    global_vars_compared = 0

    for label in llm_dirs.keys():
        llm_dir = llm_dirs[label]
        local_dir = local_dirs[label]

        print(f"{'=' * 15} 【{label}】 {'=' * 15}")

        # 接收新增的两个列表
        valid_files, res_matches, all_matches, vars_matched, vars_compared, all_match_files, result_only_match_files = compare_directories(
            llm_dir, local_dir)

        if valid_files > 0:
            print(f"📂 计入统计的文件数: {valid_files} (过滤掉了缺失 result 的文件)")
            print(f"🎯 'result' 相同文件数: {res_matches} (文件占比 {res_matches / valid_files:.1%})")
            print(f"🌟 所有变量相同文件数: {all_matches} (文件占比 {all_matches / valid_files:.1%})")
            print(
                f"🧩 相同变量累加总数: {vars_matched} / {vars_compared} (变量维度匹配率 {vars_matched / vars_compared:.1%})")

            # --- 新增：打印特定文件名 ---
            if all_match_files:
                print(f"   ✅ [全变量相同] 的文件名:")
                # 使用逗号拼接打印，如果文件很多可以换行，这里采用直接拼接
                print(f"      {', '.join(all_match_files)}")

            if result_only_match_files:
                print(f"   ⚠️ [result相同但有其他变量不同] 的文件名:")
                print(f"      {', '.join(result_only_match_files)}")
            # --------------------------

            print()  # 打印空行分割
        else:
            print("⚠️ 未找到含有 result 的共同文件或目录不存在。\n")

        global_files += valid_files
        global_result_matches += res_matches
        global_all_matches += all_matches
        global_vars_matched += vars_matched
        global_vars_compared += vars_compared

    # 打印全局汇总
    print("📊" + "=" * 30 + " 总体统计结果 " + "=" * 30)
    print(f"总计有效对比文件数: {global_files}")
    if global_files > 0:
        print(
            f"✨ 总计 'result' 相同文件数: {global_result_matches} (总体文件占比 {global_result_matches / global_files:.1%})")
        print(f"✨ 总计 所有变量相同文件数: {global_all_matches} (总体文件占比 {global_all_matches / global_files:.1%})")
        if global_vars_compared > 0:
            print(
                f"🧩 总计 相同变量累加数量: {global_vars_matched} / {global_vars_compared} (总体变量匹配率 {global_vars_matched / global_vars_compared:.1%})")


if __name__ == "__main__":
    main()