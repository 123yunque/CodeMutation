import copy
import re
import sys
from pathlib import Path
from typing import List, Tuple

from cfg_builder import build_cfg


MAX_BLOCK_STEPS = 500


def detect_output_var(source_code: str) -> str:
    if re.search(r"\bresult\s*\.?\s*append\b", source_code):
        return "result"
    if re.search(r"f\.write\(str\(result\)\)", source_code):
        return "result"

    match = re.search(r"\breturn\s+(\w+)", source_code)
    if match:
        return match.group(1)

    return "result"


def trace_block_and_output(
    filepath: str,
    output_var: str | None = None,
    target_function: str | None = "fun1",
) -> Tuple[List[str], List, List[Tuple[str, object]]]:
    path = str(Path(filepath).resolve())
    source_code = Path(path).read_text(encoding="utf-8")

    if output_var is None:
        output_var = detect_output_var(source_code)

    line_to_block, _ = build_cfg(source_code)
    if not line_to_block:
        return [], [], []

    block_sequence: List[str] = []
    value_sequence: List[object] = []
    paired: List[Tuple[str, object]] = []
    current_block = [None]
    last_value = [object()]
    line_events = [0]

    def tracer(frame, event, arg):
        if event != "line":
            return tracer
        if frame.f_code.co_filename != path:
            return tracer
        if target_function and frame.f_code.co_name not in {target_function, "<module>"}:
            return tracer

        line_events[0] += 1
        if line_events[0] > MAX_BLOCK_STEPS * 10:
            return None

        new_block = line_to_block.get(frame.f_lineno)
        if new_block is None or new_block == current_block[0]:
            return tracer

        current_block[0] = new_block
        if len(block_sequence) >= MAX_BLOCK_STEPS:
            if not block_sequence or block_sequence[-1] != "TRUNCATED":
                block_sequence.append("TRUNCATED")
            return tracer

        value = _safe_copy(frame.f_locals.get(output_var))
        block_sequence.append(new_block)
        paired.append((new_block, value))

        if not value_sequence or str(value) != str(last_value[0]):
            value_sequence.append(value)
            last_value[0] = value

        return tracer

    code = compile(source_code, path, "exec")
    namespace = {"__file__": path, "__name__": "__main__"}
    sys.settrace(tracer)
    try:
        exec(code, namespace)
    except Exception:
        pass
    finally:
        sys.settrace(None)

    return block_sequence, value_sequence, paired


def _safe_copy(value):
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    try:
        return copy.deepcopy(value)
    except Exception:
        return str(value)


def format_trace_result(
    block_seq: List[str],
    val_seq: List,
    output_var: str = "result",
) -> str:
    return f"'block_sequence': {block_seq}\n'{output_var}': {val_seq}\n"


if __name__ == "__main__":
    target = sys.argv[1]
    source = Path(target).read_text(encoding="utf-8")
    var_name = detect_output_var(source)
    blocks, values, _ = trace_block_and_output(target, output_var=var_name)
    print(format_trace_result(blocks, values, var_name))
