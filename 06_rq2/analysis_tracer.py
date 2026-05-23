# analysis_tracer.py
import sys
import json
import copy
import types

# 不追踪的变量名
SKIP_VARS = {"inputs","inp"}

def trace_variables(filepath: str) -> dict:
    var_sequences = {}
    prev_locals = {}

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != filepath:
            return tracer

        if event in ("line", "return"):
            cur_locals = frame.f_locals.copy()

            for var, val in cur_locals.items():
                if var.startswith("__"):
                    continue
                if var in SKIP_VARS:
                    continue
                if callable(val):
                    continue
                # 排除 import 进来的模块
                if isinstance(val, types.ModuleType):
                    continue

                prev_val = prev_locals.get(var, object())

                if var not in prev_locals or prev_val != val:
                    try:
                        json.dumps(val)
                        safe_val = copy.deepcopy(val)
                    except (TypeError, ValueError):
                        safe_val = str(val)

                    if var not in var_sequences:
                        var_sequences[var] = []
                    var_sequences[var].append(safe_val)
                    prev_locals[var] = copy.deepcopy(val) if isinstance(val, (list, dict, set)) else val

        return tracer

    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    code = compile(source, filepath, "exec")
    ns = {}
    sys.settrace(tracer)
    try:
        exec(code, ns)
    finally:
        sys.settrace(None)

    return var_sequences


def format_result(var_sequences: dict) -> str:
    lines = []
    # lines = ["=== 变量变化序列收集结果 ==="]
    for var, vals in var_sequences.items():
        lines.append(f"'{var}': {vals}")
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "output_mbppplus_new/task_11/sample_original_correct.py.orig"
    result = trace_variables(path)
    print(format_result(result))