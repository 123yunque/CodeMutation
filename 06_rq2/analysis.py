import os
import json
import traceback
from dynapyt.analyses.BaseAnalysis import BaseAnalysis


def hard_log(msg):
    with open("dynapyt_hard_debug.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")


class BatchVariableTracker(BaseAnalysis):
    def __init__(self, **kwargs):
        super().__init__()
        self.var_sequences = {}
        self.ast_cache = {}
        hard_log("\n" + "=" * 60)
        hard_log("🚀 [__init__] 启动绝对完美版分析器！(精准匹配 JSON 文件名)")

    def _get_var_name(self, dyn_ast_path, iid):
        clean_path = dyn_ast_path.replace(".orig", "")

        # 加载 JSON（只加载一次）
        if clean_path not in self.ast_cache:
            dir_name = os.path.dirname(clean_path)
            base_name = os.path.splitext(os.path.basename(clean_path))[0]
            actual_json = os.path.join(dir_name, f"{base_name}-dynapyt.json")

            if os.path.exists(actual_json):
                try:
                    with open(actual_json, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    # 只取 iid_to_location 部分
                    self.ast_cache[clean_path] = raw.get("iid_to_location", {})
                except Exception as e:
                    hard_log(f"❌ JSON 加载失败: {e}")
                    self.ast_cache[clean_path] = {}
            else:
                hard_log(f"❌ JSON 不存在: {actual_json}")
                self.ast_cache[clean_path] = {}

        loc = self.ast_cache.get(clean_path, {}).get(str(iid))
        if not loc:
            return f"var_iid_{iid}"

        start_line = loc.get("start_line")
        start_col = loc.get("start_column", 0)
        end_line = loc.get("end_line")
        end_col = loc.get("end_column", 0)

        # 优先读 .orig 原始文件
        orig_path = loc.get("file", "")
        if not os.path.exists(orig_path):
            orig_path = clean_path + ".orig"
        if not os.path.exists(orig_path):
            orig_path = clean_path

        return self._extract_varname_from_source(orig_path, start_line, start_col, end_line, end_col, iid)

    def _extract_varname_from_source(self, file_path, start_line, start_col, end_line, end_col, iid):
        """根据行列号从源码中精准提取变量名"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 提取节点跨越的原始代码片段
            if start_line == end_line:
                snippet = lines[start_line - 1][start_col:end_col].strip()
            else:
                first = lines[start_line - 1][start_col:]
                middle = "".join(lines[start_line:end_line - 1])
                last = lines[end_line - 1][:end_col]
                snippet = (first + middle + last).strip()

            hard_log(f"  iid={iid} 原始片段: {repr(snippet)}")

            # ── 策略1：赋值语句左侧，如 "x = ..." 或 "x: int = ..." ──
            if "=" in snippet and "==" not in snippet and "!=" not in snippet:
                left = snippet.split("=")[0].strip()
                left = left.split(":")[0].strip()  # 去类型注解
                if left.isidentifier():
                    return left
                # 多目标赋值：只取第一个，如 "a, b = ..."
                parts = [p.strip() for p in left.split(",")]
                if all(p.isidentifier() for p in parts):
                    return left  # 返回完整左侧，如 "a, b"

            # ── 策略2：for 循环变量，如 "for x in ..." ──
            if snippet.startswith("for ") and " in " in snippet:
                loop_var = snippet[4:snippet.index(" in ")].strip()
                if loop_var.isidentifier():
                    return loop_var

            # ── 策略3：片段本身就是一个变量名（单独的 Name 节点）──
            candidate = snippet.split("\n")[0].strip()
            if candidate.isidentifier():
                return candidate

            # ── 策略4：增强赋值，如 "x += 1" ──
            for op in ["+=", "-=", "*=", "/=", "//=", "%=", "**=", "&=", "|=", "^="]:
                if op in snippet:
                    left = snippet.split(op)[0].strip()
                    if left.isidentifier():
                        return left

        except Exception as e:
            hard_log(f"❌ 源码提取失败: {e}\n{traceback.format_exc()}")

        return f"var_iid_{iid}"

    def write(self, dyn_ast, iid, *args):
        try:
            var_name = self._get_var_name(dyn_ast, iid)
            val = args[-1] if args else None

            if var_name not in self.var_sequences:
                self.var_sequences[var_name] = []

            safe_val = val if isinstance(val, (int, float, str, bool)) else str(val)
            self.var_sequences[var_name].append(safe_val)

        except Exception as e:
            hard_log(f"❌ [write] 致命错误: {e}")
            hard_log(traceback.format_exc())

        return args[-1] if args else None

    def end_execution(self):
        task_name = os.environ.get("DYNAPYT_TASK_NAME", "manual_test")
        output_dir = os.environ.get("DYNAPYT_OUTPUT_DIR", "original_local")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{task_name}.txt")

        lines = []
        for v, seq in self.var_sequences.items():
            lines.append(f"'{v}': {seq}")

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass