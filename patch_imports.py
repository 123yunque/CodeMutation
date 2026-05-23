"""
patch_imports.py
在执行 reorganize.sh 之后运行此脚本，自动修补所有移入子目录的文件的路径引用。

运行方式：python patch_imports.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent

# ──────────────────────────────────────────────────────────────
# 公共头部：注入到每个被修补文件的顶部
# ──────────────────────────────────────────────────────────────
SYS_PATH_HEADER = '''\
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
from paths import (
    ROOT, CONFIG, CONFIG1, MBPP_DIR,
    EQUIV_TRANSFORM, NON_EQUIV_TRANSFORM,
    LLM_ORIGINAL, LLM_EQUIV, LLM_NON_EQUIV,
    LOCAL_ORIGINAL, LOCAL_EQUIV, LOCAL_NON_EQUIV,
    LLM_TRACE_ORIGINAL, LLM_TRACE_EQUIV, LLM_TRACE_NON_EQUIV,
)
'''

# ──────────────────────────────────────────────────────────────
# 针对每个文件的具体替换规则
# 格式：{ 文件相对路径: [(旧字符串, 新字符串), ...] }
# ──────────────────────────────────────────────────────────────
PATCHES = {

    # ── 05_rq1/run_tasks.py ──────────────────────────────────
    "05_rq1/run_tasks.py": [
        # import utils（同目录，不需要改，Python 会自动找同目录）
        # 只需修复 config1.json 的读取路径
        (
            'open("config1.json"',
            'open(str(CONFIG1)'
        ),
    ],

    # ── 05_rq1/evaluate.py ───────────────────────────────────
    "05_rq1/evaluate.py": [
        (
            'original_dir = "sample_output_LLMs_original_code/minimax"',
            'original_dir = str(LLM_ORIGINAL / "minimax")'
        ),
        (
            'equivalent_dir = "sample_output_LLMs_equivalent_code/minimax"',
            'equivalent_dir = str(LLM_EQUIV / "minimax")'
        ),
        (
            'non_equivalent_dir = "sample_output_LLMs_non_equivalent_code/minimax"',
            'non_equivalent_dir = str(LLM_NON_EQUIV / "minimax")'
        ),
        (
            'mbpp_dir = "output_mbppplus_new"',
            'mbpp_dir = str(MBPP_DIR)'
        ),
    ],

    # ── 05_rq1/utils.py ──────────────────────────────────────
    # utils.py 的路径都是外部传入，本身不需要修改路径
    # 只需确保 config1.json 读取时使用正确路径（由 run_tasks.py 负责）

    # ── 06_rq2/run_tracer.py ─────────────────────────────────
    "06_rq2/run_tracer.py": [
        # from analysis_tracer import → 同目录，不需要改
        (
            'TARGET_DIR = "output_mbppplus_new"',
            'TARGET_DIR = str(MBPP_DIR)'
        ),
        (
            'OUTPUT_DIR = "non_equivalent_local/error"',
            'OUTPUT_DIR = str(LOCAL_NON_EQUIV / "error")'
        ),
        # 若有其他 OUTPUT_DIR 变体也一并替换
        (
            'OUTPUT_DIR = "original_local/correct"',
            'OUTPUT_DIR = str(LOCAL_ORIGINAL / "correct")'
        ),
        (
            'OUTPUT_DIR = "original_local/error"',
            'OUTPUT_DIR = str(LOCAL_ORIGINAL / "error")'
        ),
        (
            'OUTPUT_DIR = "equivalent_local/correct"',
            'OUTPUT_DIR = str(LOCAL_EQUIV / "correct")'
        ),
        (
            'OUTPUT_DIR = "equivalent_local/error"',
            'OUTPUT_DIR = str(LOCAL_EQUIV / "error")'
        ),
        (
            'OUTPUT_DIR = "non_equivalent_local/correct"',
            'OUTPUT_DIR = str(LOCAL_NON_EQUIV / "correct")'
        ),
    ],

    # ── 06_rq2/run_llm_tracer.py ─────────────────────────────
    "06_rq2/run_llm_tracer.py": [
        (
            'INPUT_DIR = "output_mbppplus_new"',
            'INPUT_DIR = str(MBPP_DIR)'
        ),
        (
            'open("config1.json"',
            'open(str(CONFIG1)'
        ),
        # FILE_CONFIG 里的目录前缀改为绝对路径
        (
            '"original_llm"',
            'str(LLM_TRACE_ORIGINAL)'
        ),
        (
            '"equivalent_llm"',
            'str(LLM_TRACE_EQUIV)'
        ),
        (
            '"non_equivalent_llm"',
            'str(LLM_TRACE_NON_EQUIV)'
        ),
    ],

    # ── 06_rq2/evaluate_trace.py ─────────────────────────────
    "06_rq2/evaluate_trace.py": [
        # llm_dirs 和 local_dirs 字典的值全部替换
        (
            '"equivalent_llm/correct"',
            'str(LLM_TRACE_EQUIV / "correct")'
        ),
        (
            '"equivalent_llm/error"',
            'str(LLM_TRACE_EQUIV / "error")'
        ),
        (
            '"non_equivalent_llm/correct"',
            'str(LLM_TRACE_NON_EQUIV / "correct")'
        ),
        (
            '"non_equivalent_llm/error"',
            'str(LLM_TRACE_NON_EQUIV / "error")'
        ),
        (
            '"original_llm/correct"',
            'str(LLM_TRACE_ORIGINAL / "correct")'
        ),
        (
            '"original_llm/error"',
            'str(LLM_TRACE_ORIGINAL / "error")'
        ),
        (
            '"equivalent_local/correct"',
            'str(LOCAL_EQUIV / "correct")'
        ),
        (
            '"equivalent_local/error"',
            'str(LOCAL_EQUIV / "error")'
        ),
        (
            '"non_equivalent_local/correct"',
            'str(LOCAL_NON_EQUIV / "correct")'
        ),
        (
            '"non_equivalent_local/error"',
            'str(LOCAL_NON_EQUIV / "error")'
        ),
        (
            '"original_local/correct"',
            'str(LOCAL_ORIGINAL / "correct")'
        ),
        (
            '"original_local/error"',
            'str(LOCAL_ORIGINAL / "error")'
        ),
    ],

    # ── 04_local_exec/run_code.py ────────────────────────────
    "04_local_exec/run_code.py": [
        (
            'current_dir = os.path.dirname(os.path.abspath(__file__))',
            'current_dir = str(ROOT)'
        ),
        (
            'base_dir = os.path.join(current_dir, "output_mbppplus_new")',
            'base_dir = str(MBPP_DIR)'
        ),
    ],

    # ── 04_local_exec/handle_non_equivalent.py ───────────────
    "04_local_exec/handle_non_equivalent.py": [
        # 删除错误的跨目录 import（splice 文件已归档，folder 变量不应被导入）
        (
            'from splice_non_equivalent_function_and_main import folder\n',
            '# [已修复] 移除了对已归档文件的错误 import\n'
        ),
        (
            'original_dir = "non_equivalent_transform_new"',
            'original_dir = str(NON_EQUIV_TRANSFORM)'
        ),
        (
            'mbpp_dir = "output_mbppplus_new"',
            'mbpp_dir = str(MBPP_DIR)'
        ),
    ],

    # ── 02_mutation/equivalent_transform.py ──────────────────
    "02_mutation/equivalent_transform.py": [
        (
            'current_dir = os.path.dirname(os.path.abspath(__file__))',
            'current_dir = str(ROOT)'
        ),
        (
            'config_path = os.path.join(current_dir, "config.json")',
            'config_path = str(CONFIG)'
        ),
        (
            'output_path = os.path.join(current_dir, "equivalent_transform_new")',
            'output_path = str(EQUIV_TRANSFORM)'
        ),
        (
            'input_dir = os.path.join(current_dir, "output_mbppplus_new")',
            'input_dir = str(MBPP_DIR)'
        ),
    ],

    # ── 02_mutation/noequivalent_transform.py ────────────────
    "02_mutation/noequivalent_transform.py": [
        (
            'current_dir = os.path.dirname(os.path.abspath(__file__))',
            'current_dir = str(ROOT)'
        ),
        (
            'config_path = os.path.join(current_dir, "config.json")',
            'config_path = str(CONFIG)'
        ),
        (
            'output_path = os.path.join(current_dir, "non_equivalent_transform_new")',
            'output_path = str(NON_EQUIV_TRANSFORM)'
        ),
        (
            'input_dir = os.path.join(current_dir, "output_mbppplus_new")',
            'input_dir = str(MBPP_DIR)'
        ),
    ],

    # ── 03_splice/splice_equivalent.py ───────────────────────
    "03_splice/splice_equivalent.py": [
        (
            'base_dir = "output_mbppplus_new"',
            'base_dir = str(MBPP_DIR)'
        ),
        (
            'fun_dir = "equivalent_transform_new"',
            'fun_dir = str(EQUIV_TRANSFORM)'
        ),
    ],

    # ── 03_splice/splice_non_equivalent.py ───────────────────
    "03_splice/splice_non_equivalent.py": [
        (
            'base_dir = "output_mbppplus_new"',
            'base_dir = str(MBPP_DIR)'
        ),
        (
            'fun_dir = "non_equivalent_transform_new"',
            'fun_dir = str(NON_EQUIV_TRANSFORM)'
        ),
    ],

    # ── 01_data/sample_load.py ───────────────────────────────
    "01_data/sample_load.py": [
        (
            'output_dir = "output_mbppplus_new"',
            'output_dir = str(MBPP_DIR)'
        ),
    ],
}

# ──────────────────────────────────────────────────────────────
# 执行修补
# ──────────────────────────────────────────────────────────────

HEADER_MARKER = "# [auto-patched by patch_imports.py]"


def needs_header(content: str) -> bool:
    return HEADER_MARKER not in content


def apply_patches(filepath: Path, replacements: list) -> tuple[bool, list]:
    if not filepath.exists():
        return False, [f"文件不存在: {filepath}"]

    content = filepath.read_text(encoding="utf-8")
    messages = []
    changed = False

    for old, new in replacements:
        if old in content:
            content = content.replace(old, new, 1)
            messages.append(f"  ✅ 替换: {old[:60]!r}")
            changed = True
        else:
            messages.append(f"  ⏭  未找到（可能已修改）: {old[:60]!r}")

    if changed and needs_header(content):
        # 在第一行 import 之前插入 sys.path header
        lines = content.split("\n")
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_pos = i
                break
        header_lines = [HEADER_MARKER] + SYS_PATH_HEADER.strip().split("\n") + [""]
        lines = lines[:insert_pos] + header_lines + lines[insert_pos:]
        content = "\n".join(lines)

    if changed:
        filepath.write_text(content, encoding="utf-8")

    return changed, messages


def main():
    print("🔧 开始修补路径引用...\n")
    total_changed = 0

    for rel_path, replacements in PATCHES.items():
        filepath = ROOT / rel_path
        print(f"📄 {rel_path}")
        changed, messages = apply_patches(filepath, replacements)
        for msg in messages:
            print(msg)
        if changed:
            print(f"  → 文件已更新")
            total_changed += 1
        print()

    print(f"✅ 完成！共修补了 {total_changed} 个文件。")
    print("\n验证路径配置：")
    print("  python paths.py")


if __name__ == "__main__":
    main()
