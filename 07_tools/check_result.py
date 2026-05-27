import os
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from paths import MBPP_DIR

base_dir = str(MBPP_DIR)

for root, dirs, files in os.walk(base_dir):
    # 只检查第一层子目录
    for d in dirs:
        subdir_path = os.path.join(root, d)
        result_path = os.path.join(subdir_path, "results.txt")

        if not os.path.isfile(result_path):
            print(d)
    break  # 防止递归进入更深层目录
