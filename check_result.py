import os

base_dir = "output_mbppplus"

for root, dirs, files in os.walk(base_dir):
    # 只检查第一层子目录
    for d in dirs:
        subdir_path = os.path.join(root, d)
        result_path = os.path.join(subdir_path, "results.txt")

        if not os.path.isfile(result_path):
            print(d)
    break  # 防止递归进入更深层目录
