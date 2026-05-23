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
import subprocess

# 基础目录配置
current_dir = str(ROOT)
base_dir = str(MBPP_DIR)
"""
本地执行代码
"""

def main():
    if not os.path.exists(base_dir):
        print(f"❌ 找不到目录: {base_dir}")
        return

    # 获取所有任务文件夹并排序，保证执行顺序直观
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    folders.sort()

    total = len(folders)
    success_count = 0
    fail_count = 0

    print(f"🚀 开始批量执行，共找到 {total} 个文件夹...\n")

    for folder in folders:
        subdir = os.path.join(base_dir, folder)
        script_path = os.path.join(subdir, "sample_inputs_non_equivalent.py")#等价sample_inputs_equivalent.py  非等价sample_inputs_non_equivalent.py

        if not os.path.exists(script_path):
            print(f"⏭ 跳过 {folder}: 找不到 new_sample_inputs.py")
            continue

        print(f"▶️ 正在运行: {folder}/new_sample_inputs.py ...")

        try:
            # 使用 subprocess.run 执行脚本
            # cwd=subdir 非常关键，它保证脚本的工作目录是该子文件夹，从而正确解析 __file__
            result = subprocess.run(
                ["python", "sample_inputs_non_equivalent.py"],
                cwd=subdir,
                capture_output=True,  # 捕获输出，不在控制台刷屏
                text=True,  # 将输出解码为字符串
                timeout=30  # 设置 30 秒超时，防止死循环卡死程序
            )

            if result.returncode == 0:
                print(f"   ✅ 执行成功！")
                success_count += 1
            else:
                print(f"   ❌ 执行失败 (Exit Code: {result.returncode})")
                print(f"   [错误信息]:\n{result.stderr.strip()}")
                fail_count += 1

        except subprocess.TimeoutExpired:
            print(f"   ⏳ 运行超时 (超过 30 秒)，已强制终止。")
            fail_count += 1
        except Exception as e:
            print(f"   ⚠️ 发生系统异常: {e}")
            fail_count += 1

    print("\n" + "=" * 40)
    print("📊 执行统计结果")
    print("=" * 40)
    print(f"总计: {total}")
    print(f"成功: {success_count}")
    print(f"失败/超时: {fail_count}")


if __name__ == "__main__":
    main()