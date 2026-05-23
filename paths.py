"""
paths.py  —  项目路径中枢
放在项目根目录，所有子目录里的脚本统一从这里取路径。

用法：
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))  # 把根目录加入 sys.path
    from paths import ROOT, CONFIG1, MBPP_DIR, ...
"""

from pathlib import Path

# ── 项目根目录（本文件所在位置）──────────────────────────────
ROOT = Path(__file__).parent

# ── 配置文件 ────────────────────────────────────────────────
CONFIG  = ROOT / "config.json"
CONFIG1 = ROOT / "config1.json"

# ── 原始数据集 ──────────────────────────────────────────────
MBPP_DIR            = ROOT / "output_mbppplus_new"

# ── 变异代码 ────────────────────────────────────────────────
EQUIV_TRANSFORM     = ROOT / "equivalent_transform_new"
NON_EQUIV_TRANSFORM = ROOT / "non_equivalent_transform_new"

# ── RQ1：LLM 输出预测结果 ────────────────────────────────────
LLM_ORIGINAL    = ROOT / "sample_output_LLMs_original_code"
LLM_EQUIV       = ROOT / "sample_output_LLMs_equivalent_code"
LLM_NON_EQUIV   = ROOT / "sample_output_LLMs_non_equivalent_code"

# ── RQ2：本地插桩变量序列真值 ────────────────────────────────
LOCAL_ORIGINAL  = ROOT / "original_local"
LOCAL_EQUIV     = ROOT / "equivalent_local"
LOCAL_NON_EQUIV = ROOT / "non_equivalent_local"

# ── RQ2：LLM 预测变量序列 ────────────────────────────────────
LLM_TRACE_ORIGINAL  = ROOT / "original_llm"
LLM_TRACE_EQUIV     = ROOT / "equivalent_llm"
LLM_TRACE_NON_EQUIV = ROOT / "non_equivalent_llm"


def ensure_dirs(*dirs):
    """批量创建目录（如果不存在）"""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # 运行此文件可验证所有路径是否存在
    all_paths = {
        "ROOT":              ROOT,
        "CONFIG":            CONFIG,
        "CONFIG1":           CONFIG1,
        "MBPP_DIR":          MBPP_DIR,
        "EQUIV_TRANSFORM":   EQUIV_TRANSFORM,
        "NON_EQUIV_TRANSFORM": NON_EQUIV_TRANSFORM,
    }
    print("路径验证：")
    for name, path in all_paths.items():
        status = "✅" if path.exists() else "⚠️  不存在（将在运行时创建）"
        print(f"  {name:25s} {path}  {status}")
