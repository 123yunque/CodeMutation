# [auto-patched by patch_imports.py]
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

import argparse
import json
import os
from utils import execute_task_with_threads

"""
RQ1:让模型给输出结果  控制台输入命令 👇是格式
python run_tasks.py --mode non_equivalent --output_name minimax --model_name minimaxai/minimax-m2.5
python run_tasks.py --mode non_equivalent --output_name glm --model_name z-ai/glm5
python run_tasks.py --mode equivalent --output_name minimax --model_name minimaxai/minimax-m2.5
python run_tasks.py --mode equivalent --output_name glm --model_name z-ai/glm5
python run_tasks.py --mode original --output_name minimax --model_name minimaxai/minimax-m2.5
python run_tasks.py --mode original --output_name glm --model_name z-ai/glm5
python run_tasks.py --mode non_equivalent --output_name gpt51 --model_name gpt-5.1
python run_tasks.py --mode equivalent --output_name gpt51 --model_name gpt-5.1
python run_tasks.py --mode original --output_name gpt51 --model_name gpt-5.1
"""
def main():
    # 加载配置文件
    with open(str(CONFIG1), "r", encoding="utf-8") as f:
        config = json.load(f)
    # 设置命令行参数解析
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, help="Execution mode: original, non_equivalent, equivalent")
    parser.add_argument("--output_name", required=True, help="Name for the last output directory")
    parser.add_argument("--model_name", required=True, help="Custom model name for LLM API calls")
    args = parser.parse_args()
    mode = args.mode
    if mode not in config["api_key_fields"]:
        print("❌ 未知模式！有效模式为: original, non_equivalent, equivalent")
        return
    # 动态指定输出路径和模型名称
    output_path = os.path.join(config["output_paths"][mode].rsplit("/", 1)[0], args.output_name)
    model_name = args.model_name
    # 配置其他路径和参数
    api_key = config["api_key_fields"][mode]
    input_dir = config["input_paths"][mode]
    filename = ""
    if mode == "original":
        filename = "sample_original.py"
    else:
        filename = f"sample_inputs_{mode}.py"
    # 执行任务
    execute_task_with_threads(input_dir, output_path, api_key, model_name, filename)
if __name__ == "__main__":
    main()