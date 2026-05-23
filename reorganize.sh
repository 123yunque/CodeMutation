#!/bin/bash
# reorganize.sh
# 在项目根目录下执行：bash reorganize.sh
# 功能：把所有 py 文件按流水线阶段归入子目录，不删除任何文件

set -e
ROOT="."

echo "📁 创建目录结构..."
mkdir -p "$ROOT/01_data"
mkdir -p "$ROOT/02_mutation"
mkdir -p "$ROOT/03_splice"
mkdir -p "$ROOT/04_local_exec"
mkdir -p "$ROOT/05_rq1"
mkdir -p "$ROOT/06_rq2"
mkdir -p "$ROOT/07_tools"
mkdir -p "$ROOT/archive"
mkdir -p "$ROOT/docs"

echo "📦 01_data — 数据集加载"
mv -n "$ROOT/sample_load.py"       "$ROOT/01_data/" 2>/dev/null || true
mv -n "$ROOT/load_dataset.py"      "$ROOT/01_data/" 2>/dev/null || true
mv -n "$ROOT/load_dataset_new.py"  "$ROOT/01_data/" 2>/dev/null || true

echo "📦 02_mutation — 代码变异生成"
mv -n "$ROOT/equivalent_transform.py"    "$ROOT/02_mutation/" 2>/dev/null || true
mv -n "$ROOT/noequivalent_transform.py"  "$ROOT/02_mutation/" 2>/dev/null || true

echo "📦 03_splice — 代码拼接"
# 重命名为更清晰的名字
if [ -f "$ROOT/splice_main_and_function.py" ]; then
  cp "$ROOT/splice_main_and_function.py" "$ROOT/03_splice/splice_equivalent.py"
  mv "$ROOT/splice_main_and_function.py" "$ROOT/archive/"
fi
if [ -f "$ROOT/splice_non_equivalent_function_and_main.py" ]; then
  cp "$ROOT/splice_non_equivalent_function_and_main.py" "$ROOT/03_splice/splice_non_equivalent.py"
  mv "$ROOT/splice_non_equivalent_function_and_main.py" "$ROOT/archive/"
fi

echo "📦 04_local_exec — 本地执行 & 无效变异过滤"
mv -n "$ROOT/run_code.py"                "$ROOT/04_local_exec/" 2>/dev/null || true
mv -n "$ROOT/handle_non_equivalent.py"   "$ROOT/04_local_exec/" 2>/dev/null || true

echo "📦 05_rq1 — RQ1 LLM 输出预测 & 评估"
mv -n "$ROOT/run_tasks.py"   "$ROOT/05_rq1/" 2>/dev/null || true
mv -n "$ROOT/utils.py"       "$ROOT/05_rq1/" 2>/dev/null || true
mv -n "$ROOT/evaluate.py"    "$ROOT/05_rq1/" 2>/dev/null || true

echo "📦 06_rq2 — RQ2 执行轨迹分析 & 评估"
mv -n "$ROOT/analysis_tracer.py"   "$ROOT/06_rq2/" 2>/dev/null || true
mv -n "$ROOT/run_tracer.py"        "$ROOT/06_rq2/" 2>/dev/null || true
mv -n "$ROOT/run_llm_tracer.py"    "$ROOT/06_rq2/" 2>/dev/null || true
mv -n "$ROOT/evaluate_trace.py"    "$ROOT/06_rq2/" 2>/dev/null || true
mv -n "$ROOT/analysis.py"          "$ROOT/06_rq2/" 2>/dev/null || true
mv -n "$ROOT/batch_run_analysis.py" "$ROOT/06_rq2/" 2>/dev/null || true  # 也属于 RQ2

echo "📦 07_tools — 工具脚本"
mv -n "$ROOT/check_output.py"          "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/check_result.py"          "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/check_trace_output.py"    "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/check_transform_code.py"  "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/split_output.py"          "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/split_trace.py"           "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/delete_error.py"          "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/clean_dynapyt_pragma.py"  "$ROOT/07_tools/" 2>/dev/null || true
mv -n "$ROOT/handle_diffinputs.py"     "$ROOT/07_tools/" 2>/dev/null || true

echo "📦 archive — 旧版/实验性脚本（不参与主流程）"
mv -n "$ROOT/equivalent_gpt.py"              "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/equivalent_gemini.py"           "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/equivalent_claude.py"           "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/sample_gpt.py"                  "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/sample_original_gemini.py"      "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/sample_equivalent_gemini.py"    "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/sample_non_equivalent_gemini.py" "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/sample_code.py"                 "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/splice_code_and_log.py"         "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/evaluate_equivalent.py"         "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/run_load_dataset.py"            "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/model.py"                       "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/demo.py"                        "$ROOT/archive/" 2>/dev/null || true
mv -n "$ROOT/main.py"                        "$ROOT/archive/" 2>/dev/null || true

echo "📦 docs — 文档"
mv -n "$ROOT/PROJECT_FLOW.md"     "$ROOT/docs/" 2>/dev/null || true
mv -n "$ROOT/PROJECT_PIPELINE.md" "$ROOT/docs/" 2>/dev/null || true

echo ""
echo "✅ 整理完成！新目录结构："
find "$ROOT" -maxdepth 2 -name "*.py" -o -name "*.md" -o -name "*.json" | \
  grep -v "__pycache__" | grep -v ".pyc" | sort
