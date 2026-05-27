import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
base_dir = os.path.join(parent_dir, "output_mbppplus_new")
print(base_dir)
TARGET_FILES = {
    "sample_original__correct.py",
    "sample_original__error.py",
    "sample_error.py",
    "sample_correct.py"
}

for root, dirs, files in os.walk(base_dir):
    for filename in files:
        if filename in TARGET_FILES:
            file_path = os.path.join(root, filename)
            print(f"删除：{file_path}")
            try:
                os.remove(file_path)
                print("✔ 删除成功")
            except Exception as e:
                print(f"⛔ 删除失败：{file_path}, 错误：{e}")
