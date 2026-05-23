import os
import re


def update_inputs(output_mbppplus_dir, equivalent_transform_dir):
    # 获取所有需要处理的任务（从equivalent_transform中提取数字）
    transform_files = [f for f in os.listdir(equivalent_transform_dir)
                       if f.startswith('task_') and f.endswith('.py')]

    for tf in transform_files:
        # 提取任务数字（如 task_2.py -> 2）
        task_num = re.search(r'task_(\d+)\.py', tf).group(1)

        # 源文件路径（output_mbppplus中的combined.py）
        src_file = os.path.join(output_mbppplus_dir, f'task_{task_num}', 'combined.py')

        # 目标文件路径（equivalent_transform中的task_X.py）
        dst_file = os.path.join(equivalent_transform_dir, tf)

        if not os.path.exists(src_file):
            print(f"警告: {src_file} 不存在，跳过")
            continue

        # 从源文件提取inputs行
        with open(src_file, 'r', encoding='utf-8') as f:
            src_content = f.readlines()

        inputs_line = None
        for line in src_content:
            if line.strip().startswith('inputs ='):
                inputs_line = line
                break

        if inputs_line:
            # 更新目标文件
            with open(dst_file, 'r+', encoding='utf-8') as f:
                content = f.readlines()
                f.seek(0)

                updated = False
                for line in content:
                    if line.strip().startswith('inputs ='):
                        f.write(inputs_line)
                        updated = True
                    else:
                        f.write(line)

                if updated:
                    print(f"已更新: {dst_file}")
                else:
                    print(f"未找到inputs行: {dst_file}")


# 使用实际路径
output_dir = r"C:\study\code\llm_empirical_study\output_mbppplus"
transform_dir = r"C:\study\code\llm_empirical_study\equivalent_transform"
update_inputs(output_dir, transform_dir)
