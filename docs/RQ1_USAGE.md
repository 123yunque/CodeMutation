# RQ1 使用说明

本文档只描述当前工程化重构后的 RQ1 使用方式。旧入口文件已经删除，不再使用 `sample_load.py`、`run_code.py`、`run_tasks.py`、`evaluate.py` 等旧命令。

## 1. 当前代码结构

```text
rq1_config.py                 # RQ1 全局配置：mode、文件名、结果路径
pipeline_main.py              # RQ1 本地执行/验证/重试总入口

01_data/
  data_main.py                # 数据准备入口
  data_utils.py               # 数据加载、输入解析、任务落盘

02_mutation/
  mutation_main.py            # 变异代码生成入口
  mutation_utils.py           # prompt 与变异生成工具
  mutation_runner.py          # LLM 调用和代码校验
pipeline_lib.py               # pipeline 业务编排函数

03_splice/
  splice_main.py              # sample 脚本生成入口
  splice_utils.py             # 函数识别、输入读取、脚本拼接

04_local_exec/
  exec_main.py                # 本地执行与不等价比较入口
  exec_utils.py               # 子进程执行、结果比较

05_rq1/
  rq1_main.py                 # RQ1 LLM 执行与评估入口
  rq1_utils.py                # LLM 执行、结果比较、报告统计
```

## 2. RQ1 流程

RQ1 分为两部分：

```text
前置任务：
01_data -> 02_mutation -> 03_splice -> 04_local_exec

正式任务：
05_rq1
```

前置任务负责准备原始代码、生成等价/不等价变异、拼接可执行 sample、生成本地标准结果。

正式任务负责让 LLM 执行 sample 脚本，并把 LLM 输出和本地结果比较。

## 3. 数据准备

如果需要重新生成 `output_mbppplus_new/task_x`：

```powershell
python 01_data\data_main.py --sample_size 10 --seed 0 --overwrite
```

快速测试：

```powershell
python 01_data\data_main.py --limit 5 --sample_size 10 --seed 0 --overwrite
```

通常已经有 `output_mbppplus_new` 时，不需要重复运行 01。

## 4. 生成变异代码

生成等价变异：

```powershell
python 02_mutation\mutation_main.py --mode equivalent --max_workers 2
```

生成不等价变异：

```powershell
python 02_mutation\mutation_main.py --mode non_equivalent --max_workers 2
```

快速测试：

```powershell
python 02_mutation\mutation_main.py --mode equivalent --limit 5 --max_workers 1
python 02_mutation\mutation_main.py --mode non_equivalent --limit 5 --max_workers 1
```

强制覆盖已有变异结果：

```powershell
python 02_mutation\mutation_main.py --mode equivalent --overwrite
python 02_mutation\mutation_main.py --mode non_equivalent --overwrite
```

输出目录：

```text
equivalent_transform_new/
non_equivalent_transform_new/
```

## 5. 拼接可执行 sample

生成全部 sample 脚本：

```powershell
python 03_splice\splice_main.py --mode all
```

只生成某一类：

```powershell
python 03_splice\splice_main.py --mode original
python 03_splice\splice_main.py --mode equivalent
python 03_splice\splice_main.py --mode non_equivalent
```

每个 task 目录下会生成：

```text
sample_inputs.py
sample_original.py
sample_inputs_equivalent.py
sample_inputs_non_equivalent.py
```

这些文件会读取 `inputs`，调用目标函数，并写入本地结果。

## 6. 本地执行

执行全部模式，并生成不等价比较结果：

```powershell
python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent
```

只执行单个模式：

```powershell
python 04_local_exec\exec_main.py --mode original --timeout 30
python 04_local_exec\exec_main.py --mode equivalent --timeout 30
python 04_local_exec\exec_main.py --mode non_equivalent --timeout 30
```

快速测试：

```powershell
python 04_local_exec\exec_main.py --mode equivalent --limit 5 --timeout 30
```

本地结果文件：

```text
sample_code_results.txt
sample_code_results_equivalent.txt
sample_code_results_non_equivalent.txt
sample_code_compare_results.txt
```

说明：

- `original` 和 `equivalent` 应该结果一致。
- `non_equivalent` 会先生成变异结果，再和原始结果比较。
- 如果不等价变异和原始结果相同，该输入会被标记为无效用例。
- 本地执行固定 `PYTHONHASHSEED=0`，避免 set/tuple 输出顺序导致误判。

## 7. 本地验证变异质量

只使用已有执行结果验证。默认不重新执行本地 sample，不调用 LLM retry：

```powershell
python pipeline_main.py
```

重新执行本地 sample 后再验证：

```powershell
python pipeline_main.py --run_exec
```

快速验证：

```powershell
python pipeline_main.py --limit 5
```

对失败变异进行 LLM feedback retry：

```powershell
python pipeline_main.py --retry
```

retry 前后都重新执行本地 sample：

```powershell
python pipeline_main.py --run_exec --retry
```

报告输出：

```text
reports/mutation_failures.json
reports/mutation_failures_after_retry.json
```

当前推荐先看等价变异结果：

```text
Equivalent:
Passed 越接近 Total 越好。
Missing 通常表示原始 task 本身不可执行或结果文件缺失。
```

## 8. 运行 RQ1 正式任务

RQ1 正式任务会让 LLM 执行 sample 脚本，并把 LLM 输出保存到对应目录。

运行 original：

```powershell
python 05_rq1\rq1_main.py run --mode original --output_name gpt51 --model_name gpt-5.1 --max_workers 2
```

运行 equivalent：

```powershell
python 05_rq1\rq1_main.py run --mode equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
```

运行 non_equivalent：

```powershell
python 05_rq1\rq1_main.py run --mode non_equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
```

覆盖已有 LLM 输出：

```powershell
python 05_rq1\rq1_main.py run --mode equivalent --output_name gpt51 --model_name gpt-5.1 --overwrite
```

## 9. 评估 RQ1 结果

评估全部模式：

```powershell
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51
```

输出 JSON 报告：

```powershell
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51 --report reports\rq1_gpt51.json
```

不刷新 correct/error 输入文件：

```powershell
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51 --no_write_inputs
```

## 10. 推荐日常命令

已有变异代码时，重新生成 sample、执行并验证：

```powershell
python 03_splice\splice_main.py --mode all
python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent
python pipeline_main.py
```

完整前置流程：

```powershell
python 02_mutation\mutation_main.py --mode equivalent --max_workers 2
python 02_mutation\mutation_main.py --mode non_equivalent --max_workers 2
python 03_splice\splice_main.py --mode all
python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent
python pipeline_main.py
```

完整 RQ1 正式流程：

```powershell
python 05_rq1\rq1_main.py run --mode original --output_name gpt51 --model_name gpt-5.1 --max_workers 2
python 05_rq1\rq1_main.py run --mode equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
python 05_rq1\rq1_main.py run --mode non_equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51 --report reports\rq1_gpt51.json
```

## 11. 配置要求

`config1.json` 需要包含：

```json
{
  "model_name": "gpt-5.1",
  "yunwu_base_url": "...",
  "api_key_fields": {
    "original": "...",
    "equivalent": "...",
    "non_equivalent": "..."
  },
  "input_paths": {
    "original": "output_mbppplus_new",
    "equivalent": "output_mbppplus_new",
    "non_equivalent": "output_mbppplus_new"
  }
}
```

如果 API key 使用环境变量，格式可以是：

```json
"original": "${OPENAI_API_KEY}"
```

## 12. 旧入口说明

以下旧入口已经删除：

```text
01_data/sample_load.py
01_data/load_dataset.py
01_data/load_dataset_new.py
02_mutation/equivalent_transform.py
02_mutation/noequivalent_transform.py
03_splice/sample_code.py
03_splice/splice_equivalent.py
03_splice/splice_non_equivalent.py
04_local_exec/run_code.py
04_local_exec/handle_non_equivalent.py
05_rq1/run_tasks.py
05_rq1/evaluate.py
05_rq1/utils.py
05_rq1/rq1_config.py
```

后续只使用本文档中的新入口。
