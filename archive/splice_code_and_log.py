import os

base_dir = "output_mbppplus_new"
fun_dir = "equivalent_transform_new"

base_output_path = r"""
import sys
import json
import threading
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE = os.path.join(BASE_DIR, "variable_trace.jsonl")

# 清空日志文件
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("")

# 存储每个 frame 的变量状态（用于检测变化）
_last_vars = {}
_lock = threading.Lock()

def deep_repr(obj, depth=2):
    if depth == 0:
        return f"<{type(obj).__name__}>"

    # 基本类型
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj

    # 列表/元组
    if isinstance(obj, (list, tuple)):
        return [deep_repr(i, depth - 1) for i in obj]

    # 字典
    if isinstance(obj, dict):
        return {k: deep_repr(v, depth - 1) for k, v in obj.items()}

    # 类实例
    if hasattr(obj, "__dict__"):
        return {
            "__class__": obj.__class__.__name__,
            **{k: deep_repr(v, depth - 1) for k, v in obj.__dict__.items()}
        }

    # 其他类型
    try:
        return repr(obj)
    except:
        return f"<unprintable {type(obj).__name__}>"

def is_user_variable(name, value):
    # 排除 Python 内部自动注入变量
    if name.startswith("__") and name.endswith("__"):
        return False
    # 排除函数、模块
    if callable(value):
        return False
    # 排除模块对象
    if type(value).__name__ in ("module", "function", "builtin_function_or_method"):
        return False
    # 排除 frame 对象本身
    if type(value).__name__.endswith("frame"):
        return False
    return True

def trace_variables(frame, event, arg):
    if event != "line":
        return trace_variables

    code = frame.f_code
    func_name = code.co_name
    lineno = frame.f_lineno

    # 读取局部变量
    local_vars = frame.f_locals

    # 唯一标识函数调用 frame
    frame_id = id(frame)

    changes = {}

    # 获取前一次状态
    old_vars = _last_vars.get(frame_id, {})

    # 检查变量变化
    for k, v in local_vars.items():
        if not is_user_variable(k, v):
            continue

        value_repr = deep_repr(v)
        if k not in old_vars or old_vars[k] != value_repr:
            changes[k] = value_repr

    # 仅在变量变化时写入日志
    if changes:
        with _lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "func": func_name,
                    "line": lineno,
                    "changes": changes
                }, ensure_ascii=False) + "\n")

        # 更新状态
        _last_vars[frame_id] = {
            k: deep_repr(v)
            for k, v in local_vars.items() if is_user_variable(k, v)
        }

    return trace_variables


# 启动追踪
sys.settrace(trace_variables)
"""

close_log = "sys.settrace(None)"
for folder in os.listdir(base_dir):
    subdir = os.path.join(base_dir, folder)

    fun_name = folder+".py"

    if not os.path.isdir(subdir):
        continue

    code_path = os.path.join(base_dir,folder, "sample_inputs.py")
    output_path = os.path.join(subdir, "output_log.py")

    inputs = []

    # 如果缺少文件则跳过
    if folder.startswith("task_"):
        try:
            num = int(folder.split("_")[1])
            if num > 226:
                continue
        except:
            pass

    # 读取 code.py
    with open(code_path, "r", encoding="utf-8") as f:
        code_content = f.read()

    # 合并写入新的文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(base_output_path)
        f.write(code_content)
        f.write(close_log)
        # f.writelines(last_11_lines)

    print(f"已生成: {output_path}")
