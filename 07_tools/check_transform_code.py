import os
import re

# 根路径（你可以根据实际情况修改为绝对路径）
base_dir = os.path.dirname(os.path.abspath(__file__))
eq_dir = os.path.join(base_dir, "non_equivalent_transform")
mbpp_dir = os.path.join(base_dir, "output_mbppplus")

# 匹配以 input 或 inputs 开头的行（多行模式）
line_pattern = re.compile(r'^\s*inputs?\b.*', re.MULTILINE)

def extract_rhs_after_equals(file_path):
    """
    提取以 input(s) 开头的行中 '=' 号后的 RHS。
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = line_pattern.search(content)
    if not match:
        return None

    line = match.group(0).rstrip("\n")

    if '=' not in line:
        return None

    rhs = line.split('=', 1)[1]

    # 删除行内注释（简单版）
    if '#' in rhs:
        rhs = rhs.split('#', 1)[0]

    rhs = rhs.strip()
    rhs = re.sub(r'\s+', ' ', rhs)
    return rhs


def replace_rhs_in_file(file_path, new_rhs):
    """
    将 file_path 中 input(s) 开头的那一行的 '=' 号后的内容替换为 new_rhs。
    保留该行的前导空格、变量名、等号前面的内容（不改变缩进格式）。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    def replacer(match):
        line = match.group(0)
        # 保留前半部分（直到等号）
        before = line.split('=', 1)[0]
        # 拼接新的 RHS，确保行尾不会添加多余空格
        return before + " = " + new_rhs

    new_content = line_pattern.sub(replacer, content, count=1)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)


same = []
diff = []
missing = []

for filename in os.listdir(eq_dir):
    if not filename.startswith("task_") or not filename.endswith(".py"):
        continue

    task_id = filename.replace(".py", "")
    eq_path = os.path.join(eq_dir, filename)

    mbpp_folder = os.path.join(mbpp_dir, task_id)
    mbpp_file = os.path.join(mbpp_folder, "combined.py")

    if not os.path.exists(mbpp_file):
        missing.append(task_id)
        continue

    eq_rhs = extract_rhs_after_equals(eq_path)
    mbpp_rhs = extract_rhs_after_equals(mbpp_file)

    if eq_rhs is None or mbpp_rhs is None:
        diff.append(task_id)
        continue

    if eq_rhs == mbpp_rhs:
        same.append(task_id)
    else:
        diff.append(task_id)
        # ★★★ 自动修复：将 combined.py 的 RHS 替换到 task_xx.py 中
        replace_rhs_in_file(eq_path, mbpp_rhs)


print("===== 对比与修复结果 =====")
print(f"一致的文件数量: {len(same)}")
print()
print(f"不一致（已自动修复）的文件数量: {len(diff)}")
for i in diff:
    print("  -", i)
print()
print(f"缺少 combined.py 的任务数量: {len(missing)}")
for m in missing:
    print("  -", m)
