import os
import subprocess

base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_mbppplus_new")

for root, dirs, files in os.walk(base_dir):
    if "output_log.py" in files:
        file_path = os.path.join(root, "output_log.py")
        print(f"运行：{file_path}")

        try:
            # 使用 python 运行脚本
            result = subprocess.run(
                ["python", file_path],
                capture_output=True,
                text=True,
                timeout=300  # 可根据需要调整超时时间
            )

            print("---- 错误信息👇 ----")
            print(result.stderr)
            print("---- 错误信息👆 ----")

        except subprocess.TimeoutExpired:
            print(f"⛔ 超时：{file_path}")
        except Exception as e:
            print(f"⛔ 运行失败：{file_path}, 错误：{e}")
