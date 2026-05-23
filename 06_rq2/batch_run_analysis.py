import os
import shutil
import subprocess
from pathlib import Path

# ================= 配置区 =================
TARGET_DIR = "output_mbppplus_new"
OUTPUT_DIR = "original_local1"
ANALYSIS_MODULE = "analysis.BatchVariableTracker"
TIMEOUT_SECONDS = 15
TARGET_FILE = "sample_original_correct.py"
# ==========================================

def run_batch():
    target_path = Path(TARGET_DIR)
    py_files = sorted(target_path.rglob(TARGET_FILE))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    abs_output_dir = Path(OUTPUT_DIR).absolute()

    print(f"🔍 找到 {len(py_files)} 个目标文件 ({TARGET_FILE})，开始批量流水线...")
    print(f"📁 结果将统一输出至: {abs_output_dir}\n")

    success_count = 0
    fail_count = 0

    for py_file in py_files:
        task_name = py_file.parent.name
        print(f"▶️  [{task_name}] ", end="", flush=True)

        # ── 第一步：instrument ──────────────────────────────
        cmd_instrument = [
            "python", "-m", "dynapyt.instrument.instrument",
            "--files", str(py_file.absolute()),
            "--analysis", ANALYSIS_MODULE
        ]
        try:
            r = subprocess.run(
                cmd_instrument, timeout=TIMEOUT_SECONDS,
                capture_output=True, text=True, encoding="utf-8"  # <--- 加上这个参数
            )
            if r.returncode != 0:
                print(f"❌ instrument 失败\n{r.stderr}")
                fail_count += 1
                continue
        except subprocess.TimeoutExpired:
            print(f"⚠️  instrument 超时")
            fail_count += 1
            continue

        # ── 第二步：run ────────────────────────────────────
        # 注入环境变量，让 analysis.py 知道当前的任务名和统一输出路径
        env = os.environ.copy()
        env["DYNAPYT_TASK_NAME"] = task_name
        env["DYNAPYT_OUTPUT_DIR"] = str(abs_output_dir)
        env["PYTHONPATH"] = os.getcwd()

        cmd_run = [
            "python", "-m", "dynapyt.run_analysis",
            "--entry", str(py_file.absolute()),
            "--analysis", ANALYSIS_MODULE
        ]
        try:
            r = subprocess.run(
                cmd_run, timeout=TIMEOUT_SECONDS,
                capture_output=True, text=True, env=env, encoding="utf-8"  # <--- 加上这个参数
            )
            if r.returncode != 0:
                print(f"❌ run 失败\n{r.stderr}")
                fail_count += 1
                continue
        except subprocess.TimeoutExpired:
            print(f"⚠️  run 超时")
            fail_count += 1
            continue

        # ── 第三步：检查结果 ───────────────────────────────
        # 分析脚本现在会直接把结果写入到 abs_output_dir 下的 task_name.txt 中
        dest_txt = abs_output_dir / f"{task_name}.txt"

        if dest_txt.exists():
            print(f"✅ 已生成变量序列 → {dest_txt.name}")
            success_count += 1
        else:
            print(f"❌ 分析执行正常但未找到结果文件: {dest_txt}")
            # >>>>> 新增打印输出，看看 DynaPyt 到底在控制台输出了什么 <<<<<
            print("\n====== 🐛 运行日志 (stdout) ======")
            print(r.stdout.strip() if r.stdout.strip() else "<无标准输出>")
            print("====== 🐛 错误/警告 (stderr) ======")
            print(r.stderr.strip() if r.stderr.strip() else "<无错误日志>")
            print("==================================\n")
            fail_count += 1

    print(f"\n🎉 批量处理完成！成功: {success_count}，失败/跳过: {fail_count}")

if __name__ == "__main__":
    run_batch()