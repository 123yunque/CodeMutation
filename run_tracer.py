# batch_run.py
import os
from pathlib import Path
from analysis_tracer import trace_variables

# ================= 配置区 =================
TARGET_DIR = "output_mbppplus_new"
OUTPUT_DIR = "non_equivalent_local/error"
TARGET_FILE = "sample_non_equivalent_error.py"
# ==========================================

def format_result(var_sequences: dict) -> str:
    # lines = ["=== 变量变化序列收集结果 ==="]
    lines = []
    for var, vals in var_sequences.items():
        lines.append(f"'{var}': {vals}")
    return "\n".join(lines)


def run_batch():
    target_path = Path(TARGET_DIR)
    py_files = sorted(target_path.rglob(TARGET_FILE))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    abs_output_dir = Path(OUTPUT_DIR).absolute()

    print(f"🔍 找到 {len(py_files)} 个目标文件，开始批量追踪...")
    print(f"📁 结果输出至: {abs_output_dir}\n")

    success_count = 0
    fail_count = 0

    for py_file in py_files:
        task_name = py_file.parent.name
        print(f"▶️  [{task_name}] ", end="", flush=True)
        # if task_name == "task_733":
        #     continue
        try:
            var_sequences = trace_variables(str(py_file.absolute()))

            dest = abs_output_dir / f"{task_name}.txt"
            with open(dest, "w", encoding="utf-8") as f:
                f.write(format_result(var_sequences))

            print(f"✅ 已保存 → {dest.name}  ({len(var_sequences)} 个变量)")
            success_count += 1

        except Exception as e:
            print(f"❌ 失败: {e}")
            fail_count += 1

    print(f"\n🎉 完成！成功: {success_count}，失败: {fail_count}")


if __name__ == "__main__":
    run_batch()