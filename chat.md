# HuManEval代码修改

> 针对rq1，分析现在采用的数据集，调用的格式和内容。如何增加和使用HumanEvalPlus和CodeContestPlus数据集

<details><summary>6 previous messages</summary>

> 我先快速看一下项目里 RQ1 的入口和数据集加载逻辑，再结合当前脚本说明现状和接入新数据集的位置。
>
> 已经定位到 RQ1 主要经过 `01_data -> 02_mutation -> 03_splice -> 04_local_exec -> 05_rq1`，当前数据源看起来集中在 `01_data/data_utils.py`。我继续读加载、任务目录格式和 RQ1 调用格式。
>
> 当前 `data_utils.py` 写死了 `evalplus/mbppplus` 的 `test` split，并把每条样本转成统一的 `task_x` 文件夹。为了判断 HumanEvalPlus/CodeContestPlus 能否直接套用，还需要看后续脚本依赖哪些文件名和字段。
>
> 后续脚本依赖的是统一任务目录，而不是 HuggingFace 原始字段本身：`code.py`、`sample_code_inputs.txt`、生成后的 `sample_inputs*.py` 和本地结果文件是关键。现在我看一个实际任务样例，确认输入行和执行脚本内容。
>
> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `Hugging Face evalplus humanevalplus dataset fields`
> - Searched the web for `site:huggingface.co/datasets evalplus humanevalplus`
> - Searched the web for `EvalPlus HumanEvalPlus get_human_eval_plus source code dataset fields`
> - Searched the web for `https://github.com/evalplus/evalplus`
> - Searched the web for `"CodeContestPlus"`
>
> </details>
>
> </details>
>
> 我查了官方 EvalPlus 项目：它明确支持 HumanEval+ 和 MBPP+；`CodeContestPlus` 这个名字没有在公开 EvalPlus 入口里直接出现，所以接入时要先确认你指的是哪个 HuggingFace 数据集或本地数据文件。下面我会按“适配器层”来说明，这样即使字段不同也能接入。

</details>

针对 RQ1，当前项目实际采用的是 **MBPP+**，入口在 [01_data/data_utils.py](./01_data/data_utils.py:8)：

```python
DATASET_NAME = "evalplus/mbppplus"
DATASET_SPLIT = "test"
```

**当前数据集调用与内容**
数据准备阶段通过 `datasets.load_dataset("evalplus/mbppplus")["test"]` 读取 HuggingFace 数据集。每条样本预期至少包含：

`task_id`、`code`、`prompt`、`test`，样例里还有 `source_file`、`test_imports`、`test_list`。

项目不会直接用原始 benchmark 格式跑 RQ1，而是先规范化成任务目录：

```text
output_mbppplus_new/task_100/
  task_100.json              # 原始样本完整 JSON
  code.py                    # 标准解代码
  code_inputs.txt            # 从 test 中提取的全部 inputs
  sample_code_inputs.txt     # 随机采样后的输入，默认 10 条
  combined.py                # code + test 派生执行脚本
  results.txt                # test 中 results 的原始结果
```

`test` 字段现在被假定包含类似：

```python
inputs = [[99], [1221], [120], ...]
results = [101, 1331, 121, ...]
for i, (inp, exp) in enumerate(zip(inputs, results)):
    assertion(func(*inp), exp, 0)
```

`01_data/data_utils.py` 用正则从 `test` 里提取 `inputs = [...]`，再随机抽样写入 `sample_code_inputs.txt`。后续 `03_splice` 会把 `code.py + sample_code_inputs.txt` 拼成 `sample_inputs.py`，RQ1 LLM 实际收到的是这个可执行脚本，而不是原始 prompt。

RQ1 运行阶段在 [05_rq1/rq1_utils.py](./05_rq1/rq1_utils.py:87) 构造提示词：让模型“精确执行 Python 代码”，返回 `<result>...</result>`。然后本地结果文件与模型输出逐行比较。

**当前要注意的耦合点**
现在代码强耦合 MBPP+：

`paths.py` 写死：

```python
MBPP_DIR = ROOT / "output_mbppplus_new"
```

`rq1_config.py`、`03_splice`、`04_local_exec`、`05_rq1/evaluate` 都默认用 `MBPP_DIR`。即使 `config1.json` 里的 `input_paths` 改成别的数据集目录，`evaluate_mode()` 仍然从 `MBPP_DIR` 找本地结果，所以多数据集支持需要先解除这个硬编码。

**如何增加 HumanEvalPlus**
官方 EvalPlus 项目明确支持 HumanEval+ 和 MBPP+，README 里给出的 CLI 是 `--dataset [humaneval|mbpp]`，并说明 HumanEval+ 是扩展测试版 HumanEval，MBPP+ 是扩展测试版 MBPP。来源：EvalPlus GitHub README。

HumanEvalPlus 不能直接复用现在 MBPP+ 的 `test` 解析逻辑，因为常见字段更像：

```text
task_id
prompt
canonical_solution
entry_point
base_input
plus_input
test / contract
```

建议新增一个数据集适配层，把不同数据集都转换成项目内部统一格式：

```python
{
    "task_id": "...",
    "code": "...",              # 可执行标准解
    "entry_point": "...",       # 函数名
    "inputs": [[...], [...]],   # RQ1 输入列表
    "prompt": "...",
    "raw": item
}
```

HumanEvalPlus 的 `code` 通常应由：

```python
code = item["prompt"] + item["canonical_solution"]
```

组成；输入可用：

```python
inputs = item["base_input"] + item["plus_input"]
```

然后复用现有目录格式写：

```text
output_humanevalplus/task_HumanEval_0/
  task_HumanEval_0.json
  code.py
  code_inputs.txt
  sample_code_inputs.txt
```

任务 ID 里如果有 `/`，要转成安全文件名，例如 `HumanEval/0 -> task_HumanEval_0`。

**如何增加 CodeContestPlus**
这里需要先确认 `CodeContestPlus` 的具体来源。公开 EvalPlus README 目前直接列出的 correctness 数据集是 `humaneval` 和 `mbpp`，我没有看到官方入口里有 `CodeContestPlus` 这个 dataset 名称。若它是你已有的 HuggingFace 或本地 JSON/JSONL 数据集，接入方式仍然一样：写一个 `CodeContestPlusAdapter`，输出统一内部格式。

但 CodeContest 类数据通常比 MBPP/HumanEval 更复杂，可能不是“单函数 + 参数列表”，而是：

```text
stdin -> stdout
完整程序
多测试用例
竞赛题描述
```

如果是这种格式，当前 RQ1 的核心假设需要扩展：

当前假设：

```python
result.append(func_name(*inp))
```

CodeContest 可能需要：

```text
给程序喂 stdin
捕获 stdout
逐个 case 比较 stdout
```

也就是说 `03_splice/splice_utils.py` 要支持两种 task 类型：

```text
function_call: func(*inp)
stdio: subprocess/stdin/stdout 或 main(input)
```

**推荐改法**
最稳妥的改造顺序：

1. 新增 `dataset_name` 参数到 `01_data/data_main.py`
   例如：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset humanevalplus --output_dir output_humanevalplus --sample_size 10 --overwrite
```

2. 在 `01_data/data_utils.py` 增加适配器：

```python
DATASET_LOADERS = {
    "mbppplus": load_mbppplus_items,
    "humanevalplus": load_humanevalplus_items,
    "codecontestplus": load_codecontestplus_items,
}
```

3. 让 `save_item()` 不再依赖 MBPP+ 的 `test` 字符串正则，而是吃统一格式里的 `code` 和 `inputs`。
4. 把 `paths.py` 的 `MBPP_DIR` 改成通用 `TASK_ROOT`，或者让每个 CLI 都接受 `--input_dir/--task_root`。
5. 修复 [05_rq1/rq1_utils.py](./05_rq1/rq1_utils.py:301) 的硬编码：

```python
task_root = str(MBPP_DIR)
```

应改为从 `config1.json["input_paths"][mode]` 或 CLI 参数传入，否则评估新数据集时会跑错目录。

6. 为不同数据集使用不同输出目录，避免混淆：

```text
output_mbppplus_new
output_humanevalplus
output_codecontestplus

equivalent_transform_humanevalplus
non_equivalent_transform_humanevalplus

sample_output_LLMs_original_code/humanevalplus_gpt51
```

**使用流程示例**
HumanEvalPlus 接入后应是：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset humanevalplus --output_dir output_humanevalplus --sample_size 10 --overwrite

conda run -n Npflower python 02_mutation\mutation_main.py --mode equivalent --input_dir output_humanevalplus --output_dir equivalent_transform_humanevalplus
conda run -n Npflower python 02_mutation\mutation_main.py --mode non_equivalent --input_dir output_humanevalplus --output_dir non_equivalent_transform_humanevalplus

conda run -n Npflower python 03_splice\splice_main.py --mode all --input_dir output_humanevalplus
conda run -n Npflower python 04_local_exec\exec_main.py --mode all --input_dir output_humanevalplus --timeout 30 --compare_non_equivalent

conda run -n Npflower python 05_rq1\rq1_main.py run --mode original --input_dir output_humanevalplus --output_name humanevalplus_gpt51 --model_name gpt-5.1
conda run -n Npflower python 05_rq1\rq1_main.py evaluate --mode all --input_dir output_humanevalplus --output_name humanevalplus_gpt51
```

结论：当前 RQ1 不是通用 benchmark runner，而是 **MBPP+ 专用数据预处理 + 统一任务目录 + LLM 执行预测评估**。增加 HumanEvalPlus 比较直接，主要是字段适配；增加 CodeContestPlus 取决于它是否是函数调用型数据。如果是 stdio 竞赛题，需要扩展 splice/local_exec/RQ1 prompt 的执行模型。

> 怎么把这两个数据集完美适配现在的mbppplus，给我方案

<details><summary>2 previous messages</summary>

> 我会把方案按“尽量不改 RQ1 主流程，只在数据适配层和少量路径参数化上动刀”的方向组织。关键是先定义一个内部标准任务格式，让 MBPPPlus、HumanEvalPlus、CodeContestPlus 都转成同一种目录结构。
>
> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `EvalPlus HumanEvalPlus MBPPPlus official GitHub dataset`
> - Searched the web for `https://github.com/evalplus/evalplus`
>
> </details>
>
> </details>

</details>

方案核心：不要让 RQ1 直接认识 `MBPPPlus/HumanEvalPlus/CodeContestPlus`，而是让三者都先转换成当前 MBPPPlus 已经跑通的 **内部标准任务目录**。后面的 mutation、splice、local_exec、rq1 只吃这个标准目录。

官方 EvalPlus 当前明确支持 HumanEval+ 和 MBPP+，README 中 correctness evaluation 的入口是 `--dataset [humaneval|mbpp]`，并说明 HumanEval+ 是 80x tests，MBPP+ 是 35x tests。`CodeContestPlus` 我没有在官方 EvalPlus README 里看到同名入口，所以它需要按你实际数据源字段做适配；如果它是 stdin/stdout 型竞赛题，适配成本会明显高于 HumanEvalPlus。来源：EvalPlus GitHub README: https://github.com/evalplus/evalplus

**目标结构**
把所有数据集都落到类似当前 `output_mbppplus_new/task_x` 的结构：

```text
output_<dataset>/
  task_<safe_id>/
    task_<safe_id>.json
    meta.json
    code.py
    code_inputs.txt
    sample_code_inputs.txt
    combined.py
    results.txt
```

其中 `meta.json` 新增数据集类型信息：

```json
{
  "dataset": "humanevalplus",
  "task_id": "HumanEval/0",
  "safe_task_id": "task_HumanEval_0",
  "entry_point": "has_close_elements",
  "execution_type": "function_call"
}
```

这样后续逻辑不用猜函数名、数据源、任务类型。

**内部统一格式**
新增一个标准对象，比如 `NormalizedTask`：

```python
{
    "task_id": "HumanEval/0",
    "safe_task_id": "task_HumanEval_0",
    "dataset": "humanevalplus",
    "execution_type": "function_call",
    "entry_point": "has_close_elements",
    "prompt": "...",
    "code": "...",
    "inputs": [
        [[1.0, 2.0, 3.0], 0.5],
        [[1.0, 2.8, 3.0], 0.3]
    ],
    "raw": {...}
}
```

对当前 MBPPPlus，适配器负责从 `test` 字段解析 `inputs = [...]`，`code = item["code"]`，`entry_point` 可以用 AST 找第一个函数名。

对 HumanEvalPlus，适配器负责：

```python
code = item["prompt"] + item["canonical_solution"]
inputs = item["base_input"] + item["plus_input"]
entry_point = item["entry_point"]
```

对 CodeContestPlus，分两种情况：

如果是函数调用型：

```python
execution_type = "function_call"
code = 标准解代码
inputs = 参数列表
entry_point = 函数名
```

如果是竞赛 stdin/stdout 型：

```python
execution_type = "stdio"
code = 完整程序或 main 解法
inputs = [
    {"stdin": "...", "expected": "..."},
    {"stdin": "...", "expected": "..."}
]
```

这个分支要单独生成执行脚本，不能硬套 `func(*inp)`。

**代码改造点**
建议新增：

```text
01_data/
  adapters/
    base.py
    mbppplus.py
    humanevalplus.py
    codecontestplus.py
```

`base.py` 里放统一写盘逻辑：

```python
def write_normalized_task(task, output_dir, sample_size, seed, overwrite):
    # 写 task json、meta.json、code.py、code_inputs.txt、sample_code_inputs.txt
```

`data_main.py` 增加参数：

```powershell
--dataset mbppplus|humanevalplus|codecontestplus
--output_dir output_humanevalplus
--sample_size 10
--seed 0
--overwrite
```

当前 `data_utils.py` 里写死的：

```python
DATASET_NAME = "evalplus/mbppplus"
```

改成 registry：

```python
ADAPTERS = {
    "mbppplus": MbppPlusAdapter,
    "humanevalplus": HumanEvalPlusAdapter,
    "codecontestplus": CodeContestPlusAdapter,
}
```

**路径参数化**
现在最大问题是 `MBPP_DIR` 写死。要“完美适配”，必须把任务根目录变成参数或配置。

需要改这些地方：

```text
rq1_config.py
03_splice/splice_main.py
03_splice/splice_utils.py
04_local_exec/exec_main.py
04_local_exec/exec_utils.py
05_rq1/validate_main.py
05_rq1/validate_utils.py
05_rq1/rq1_main.py
05_rq1/rq1_utils.py
```

原则是所有 CLI 都支持：

```powershell
--input_dir output_humanevalplus
--equiv_transform_dir equivalent_transform_humanevalplus
--non_equiv_transform_dir non_equivalent_transform_humanevalplus
```

`05_rq1/rq1_utils.py` 里的：

```python
task_root = str(MBPP_DIR)
```

必须改成从参数传入，否则 evaluate 永远回 `output_mbppplus_new` 找本地结果。

**执行脚本生成**
当前 `03_splice/splice_utils.py` 默认：

```python
result.append({func_name}(*inp))
```

这适合 MBPPPlus 和 HumanEvalPlus。

建议拆成两个 builder：

```python
build_function_call_script(...)
build_stdio_script(...)
```

`function_call` 继续生成：

```python
inputs = [...]
result = []
for inp in inputs:
    result.append(entry_point(*inp))
```

`stdio` 生成：

```python
cases = [...]
for case in cases:
    run code with case["stdin"]
    capture stdout
```

如果 CodeContestPlus 是 stdio 型，RQ1 prompt 也要让 LLM 执行的是“完整脚本”，输出每个 case 的 stdout 行，而不是函数返回值。

**推荐命令形态**
MBPPPlus 保持兼容：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset mbppplus --output_dir output_mbppplus_new --sample_size 10 --overwrite
```

HumanEvalPlus：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset humanevalplus --output_dir output_humanevalplus --sample_size 10 --overwrite
conda run -n Npflower python 03_splice\splice_main.py --mode all --input_dir output_humanevalplus
conda run -n Npflower python 04_local_exec\exec_main.py --mode all --input_dir output_humanevalplus --timeout 30 --compare_non_equivalent
conda run -n Npflower python 05_rq1\rq1_main.py run --mode original --input_dir output_humanevalplus --output_name humanevalplus_gpt51 --model_name gpt-5.1
conda run -n Npflower python 05_rq1\rq1_main.py evaluate --mode all --input_dir output_humanevalplus --output_name humanevalplus_gpt51
```

CodeContestPlus：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset codecontestplus --output_dir output_codecontestplus --sample_size 10 --overwrite
```

后续命令同 HumanEvalPlus，但前提是 `execution_type` 分支已经实现。

**落地优先级**

1. 先做 `NormalizedTask + mbppplus adapter`，确保当前 MBPPPlus 输出完全不变。
2. 再做 `humanevalplus adapter`，因为它大概率仍是函数调用型，改动最小。
3. 最后做 `codecontestplus adapter`，先确认它是函数调用型还是 stdio 型；如果是 stdio，需要扩展 splice/local_exec。
4. 最后把 RQ1 evaluate、validate 全部改成接受 `input_dir`，消除 `MBPP_DIR` 硬编码。

这样改完后，MBPPPlus 是一个 adapter，不再是系统中心；HumanEvalPlus 和 CodeContestPlus 只要能转成统一任务目录，就能复用同一套 RQ1 流程。

> 如果我重新复制两个项目，这样就是直接替换数据集名字，接下来怎么改

可以。你复制两个项目分别做 `HumanEvalPlus` 和 `CodeContestPlus` 分支/目录，是最省心的方案，因为可以先不做多数据集参数化。接下来按“最小改动”改这几处。

**1. 先改数据集加载入口**

在 [01_data/data_utils.py](./01_data/data_utils.py:8) 现在是：

```python
DATASET_NAME = "evalplus/mbppplus"
DATASET_SPLIT = "test"
```

复制出的 HumanEvalPlus 项目里不要只改名字，还要改 `save_item()` 之前的数据标准化。建议加一层 `normalize_item()`：

```python
def normalize_item(item, dataset_name):
    if dataset_name == "mbppplus":
        return item

    if dataset_name == "humanevalplus":
        code = item["prompt"] + item["canonical_solution"]
        inputs = list(item.get("base_input", [])) + list(item.get("plus_input", []))
        return {
            "task_id": safe_task_id(item["task_id"]),
            "code": code,
            "prompt": item.get("prompt", ""),
            "entry_point": item["entry_point"],
            "inputs": inputs,
            "raw": dict(item),
        }

    raise ValueError(f"Unsupported dataset: {dataset_name}")
```

然后 `generate_dataset()` 里：

```python
for index, item in enumerate(dataset):
    item = normalize_item(item, DATASET_KEY)
    status = save_item(item, ...)
```

**2. 改输入提取逻辑**

现在 `save_item()` 依赖 MBPPPlus 的 `item["test"]` 字符串，并用正则抽：

```python
inputs_list = extract_inputs(test_processed)
```

HumanEvalPlus 不一定有这个 `test` 格式。改成优先用标准化后的 `item["inputs"]`：

```python
inputs_list = item.get("inputs")
if inputs_list is None:
    inputs_list = extract_inputs(test_processed)
```

这样 MBPPPlus 仍走旧逻辑，HumanEvalPlus 走新逻辑。

**3. 改 task_id 安全化**

HumanEval 的 `task_id` 常见是 `HumanEval/0`，不能直接做目录名和文件名。加：

```python
def safe_task_id(task_id):
    return str(task_id).replace("/", "_").replace("\\", "_")
```

`save_item()` 里别再强制：

```python
task_id = int(item["task_id"])
```

改成：

```python
task_id = safe_task_id(item["task_id"])
```

目录仍然生成：

```python
folder_path = os.path.join(output_dir, f"task_{task_id}")
```

HumanEval 会变成：

```text
task_HumanEval_0
```

**4. HumanEvalPlus 的函数名要用 entry_point**

当前 [03_splice/splice_utils.py](./03_splice/splice_utils.py:55) 会用 AST 找第一个函数名：

```python
func_name = get_first_function_name(code_content)
```

HumanEvalPlus 的 `prompt + canonical_solution` 通常也能找到函数，但更稳的是在数据准备阶段写 `meta.json`：

```json
{
  "entry_point": "has_close_elements"
}
```

然后 `splice_utils.py` 优先读 `meta.json`：

```python
def read_entry_point(task_dir, code_content):
    meta_path = os.path.join(task_dir, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("entry_point"):
            return meta["entry_point"]
    return get_first_function_name(code_content)
```

这样更稳。

**5. 改输出目录名**

复制项目后，建议把 [paths.py](./paths.py:22) 里的目录改掉，避免和 MBPPPlus 混：

HumanEvalPlus 项目：

```python
MBPP_DIR = ROOT / "output_humanevalplus"
EQUIV_TRANSFORM = ROOT / "equivalent_transform_humanevalplus"
NON_EQUIV_TRANSFORM = ROOT / "non_equivalent_transform_humanevalplus"

LLM_ORIGINAL = ROOT / "sample_output_LLMs_original_humanevalplus"
LLM_EQUIV = ROOT / "sample_output_LLMs_equivalent_humanevalplus"
LLM_NON_EQUIV = ROOT / "sample_output_LLMs_non_equivalent_humanevalplus"
```

变量名 `MBPP_DIR` 可以暂时不改，只改值，省事。

`config1.json` 也改：

```json
"input_paths": {
  "original": "output_humanevalplus",
  "non_equivalent": "output_humanevalplus",
  "equivalent": "output_humanevalplus"
}
```

**6. CodeContestPlus 不建议只替换数据集名**

如果 CodeContestPlus 是这种格式：

```text
stdin -> stdout
```

那不能直接适配当前 MBPPPlus 流程，因为当前核心执行模型是：

```python
result.append(func_name(*inp))
```

你需要先确认 CodeContestPlus 每条数据是不是“函数调用型”。

如果是函数调用型，按 HumanEvalPlus 一样做：

```python
code = 标准解
inputs = 参数列表
entry_point = 函数名
```

如果是 stdio 型，就要额外改 [03_splice/splice_utils.py](./03_splice/splice_utils.py:77)，新增一种脚本生成方式，不能用 `func(*inp)`。这时每个 input 应该是：

```python
{"stdin": "...", "expected": "..."}
```

执行脚本需要模拟 stdin、捕获 stdout。这个改动比 HumanEvalPlus 大很多。

**7. 推荐实际执行顺序**

HumanEvalPlus 项目先跑：

```powershell
conda run -n Npflower python 01_data\data_main.py --sample_size 10 --seed 0 --overwrite --limit 5
conda run -n Npflower python 03_splice\splice_main.py --mode original
conda run -n Npflower python 04_local_exec\exec_main.py --mode original --timeout 30 --limit 5
```

这三步通过后，再跑 mutation 和 RQ1。

CodeContestPlus 项目先只做数据准备 smoke test，不要直接全流程：

```powershell
conda run -n Npflower python 01_data\data_main.py --sample_size 10 --seed 0 --overwrite --limit 3
```

然后检查生成的：

```text
code.py
sample_code_inputs.txt
sample_inputs.py
```

如果 `sample_inputs.py` 里仍然能合理调用 `func(*inp)`，就继续；如果不是，就必须做 stdio 执行适配。

最小可行结论：HumanEvalPlus 可以按“替换数据集 + normalize inputs/code/entry_point + safe task_id”适配；CodeContestPlus 只有在函数调用型时才能同样适配，否则要新增 stdio 执行分支。

> HumanEvalPlus格式有区别吗，可以在不修改rq1以及之后rq2代码上成功运行这个数据集吗

<details><summary>1 previous message</summary>

> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `evalplus data humaneval get_human_eval_plus base_input plus_input entry_point canonical_solution`
> - Searched the web for `github evalplus get_human_eval_plus base_input plus_input`
> - Searched the web for `https://raw.githubusercontent.com/evalplus/evalplus/master/evalplus/data/humaneval.py`
>
> </details>
>
> </details>

</details>

有区别，但 **可以做到不修改 `05_rq1` 以及后续 RQ2 代码就跑 HumanEvalPlus**。前提是你在 `01_data` 数据准备阶段把 HumanEvalPlus “伪装/转换”成现在 MBPPPlus 已经生成的同款任务目录。

HumanEvalPlus 官方字段和 MBPPPlus 不一样。EvalPlus 源码里说明 HumanEvalPlus 样本包含这些键：`task_id`、`prompt`、`contract`、`canonical_solution`、`base_input`、`plus_input`、`atol`。其中 `prompt` 是函数签名和 docstring，`canonical_solution` 是标准实现，`base_input` 是原 HumanEval 输入，`plus_input` 是 EvalPlus 增强输入。来源：https://raw.githubusercontent.com/evalplus/evalplus/master/evalplus/data/humaneval.py

当前 MBPPPlus 项目依赖的不是原始数据集字段，而是准备后生成的文件：

```text
task_x/
  code.py
  sample_code_inputs.txt
  sample_inputs.py
  sample_inputs_equivalent.py
  sample_inputs_non_equivalent.py
  sample_code_results.txt
  sample_code_results_equivalent.txt
  sample_code_compare_results.txt
```

所以结论是：

```text
不改 RQ1/RQ2：可以
不改 01_data：不可以
不改 03_splice：大概率可以，但建议做一个很小的兼容增强
```

HumanEvalPlus 和 MBPPPlus 的关键差异：

```text
MBPPPlus:
  code              -> 已有完整函数实现
  test              -> 字符串，里面包含 inputs = [...] 和 results = [...]
  task_id           -> 通常是数字

HumanEvalPlus:
  prompt            -> 函数定义头 + docstring
  canonical_solution -> 函数体
  base_input        -> 原始测试输入
  plus_input        -> 增强测试输入
  task_id           -> 类似 HumanEval/0，含 /
```

你要做的是在 `01_data/data_utils.py` 里把 HumanEvalPlus 转成当前项目习惯的形式：

```python
code = item["prompt"] + item["canonical_solution"]
inputs = item["base_input"] + item["plus_input"]
task_id = item["task_id"].replace("/", "_")
```

然后照旧写：

```text
code.py                    # 写 code
code_inputs.txt            # 写全部 inputs
sample_code_inputs.txt     # 随机采样 inputs
task_x.json                # 保存原始 item 或转换后 item
```

只要 `sample_code_inputs.txt` 每行仍是一个 Python literal，例如：

```python
[[1.0, 2.0, 3.0], 0.5]
["abc", "def"]
[10]
```

现在的 `03_splice` 会生成：

```python
for inp in inputs:
    result.append(func_name(*inp))
```

这正好适合 HumanEvalPlus，因为 HumanEvalPlus 本质上也是“调用一个函数并比较返回值”的格式。

唯一需要小心的是函数名。当前 `03_splice` 用 AST 找 `code.py` 里的第一个函数名。HumanEvalPlus 的 `prompt + canonical_solution` 通常会形成完整函数定义，所以大概率能找到。但为了更稳，建议 `01_data` 额外写一个 `meta.json`：

```json
{
  "dataset": "humanevalplus",
  "task_id": "HumanEval/0",
  "entry_point": "has_close_elements"
}
```

如果你坚持不改 `03_splice`，也可以先不读 `meta.json`，直接靠 AST 找第一个函数。大多数 HumanEvalPlus 任务可以过。

最小改动方案：

1. 复制项目。
2. 改 `paths.py` 里的目录值：

```python
MBPP_DIR = ROOT / "output_humanevalplus"
EQUIV_TRANSFORM = ROOT / "equivalent_transform_humanevalplus"
NON_EQUIV_TRANSFORM = ROOT / "non_equivalent_transform_humanevalplus"
```

变量名可以暂时不改。

3. 改 `config1.json`：

```json
"input_paths": {
  "original": "output_humanevalplus",
  "equivalent": "output_humanevalplus",
  "non_equivalent": "output_humanevalplus"
}
```

4. 只改 `01_data/data_utils.py`：新增 HumanEvalPlus 加载和转换。
5. 先跑原始模式 smoke test：

```powershell
conda run -n Npflower python 01_data\data_main.py --limit 5 --sample_size 10 --seed 0 --overwrite
conda run -n Npflower python 03_splice\splice_main.py --mode original
conda run -n Npflower python 04_local_exec\exec_main.py --mode original --limit 5 --timeout 30
```

如果这三步能生成 `sample_code_results.txt`，后面的 `05_rq1` 和 RQ2 基本不用动。

最重要的一点：HumanEvalPlus 没有 MBPPPlus 那种 `test` 字符串里的 `inputs = ... results = ...` 格式，所以不能只替换数据集名字。必须在数据准备阶段把 `base_input + plus_input` 写成现在项目需要的 `sample_code_inputs.txt`。

> 是否生成同样的文件，确保rq1准确

是的，必须生成**同样的文件结构和同样的语义**，这样才能保证 RQ1 准确。

HumanEvalPlus 适配后，每个任务目录最好和 MBPPPlus 保持一致：

```text
output_humanevalplus/
  task_HumanEval_0/
    task_HumanEval_0.json
    code.py
    code_inputs.txt
    sample_code_inputs.txt
    combined.py
    results.txt
```

其中 RQ1 真正依赖的是后面流程生成/使用的这些文件：

```text
code.py
sample_code_inputs.txt
sample_inputs.py
sample_inputs_equivalent.py
sample_inputs_non_equivalent.py
sample_code_results.txt
sample_code_results_equivalent.txt
sample_code_results_non_equivalent.txt
sample_code_compare_results.txt
```

`01_data` 阶段必须保证：

```text
code.py
```

内容是完整可执行函数：

```python
<prompt>
<canonical_solution>
```

`sample_code_inputs.txt` 每行是一个可 `ast.literal_eval` 的参数列表：

```python
[[1.0, 2.0, 3.0], 0.5]
["abc"]
[10, 20]
```

这样 `03_splice` 会生成：

```python
result.append(function_name(*inp))
```

本地执行结果和 LLM 预测结果才是同一种输入、同一种输出，RQ1 比较才准确。

另外建议保留：

```text
code_inputs.txt
```

写全部 `base_input + plus_input`，再随机采样到 `sample_code_inputs.txt`。这样 HumanEvalPlus 和 MBPPPlus 的采样策略一致。

`combined.py` 和 `results.txt` 对当前后续 RQ1 主流程不是最核心，但为了完全贴合 MBPPPlus 目录，建议也生成。HumanEvalPlus 没有现成 `results` 字段，所以 `results.txt` 可以在数据准备阶段通过运行 `code.py` 对全部 inputs 计算得到，或者只在后续 `04_local_exec` 生成 `sample_code_results.txt`。为了 RQ1 准确，最关键的是 `sample_code_results.txt`，它必须由本地执行 `sample_inputs.py` 生成，而不是从数据集里猜。

检查标准：

```text
sample_code_inputs.txt 行数 == sample_code_results.txt 行数
LLM 输出 task_x.txt 行数 == sample_code_results.txt 行数
每一行都是同一个输入下的函数返回值字符串
```

只要这些成立，`05_rq1` 不需要知道这是 MBPPPlus 还是 HumanEvalPlus，评估就是准确的。

> 显示你的conda环境是什么

<details><summary>1 previous message</summary>

> 我直接查当前 shell 能看到的 conda 环境列表和激活信息。

</details>

当前这个 shell 里没有激活 conda 环境：

```text
python: E:\Anaconda\python.exe
CONDA_DEFAULT_ENV: None
```

我尝试运行 `conda info --envs` 和 `conda info`，但当前环境返回了：

```text
Access is denied.
```

所以只能确认：现在默认 `python` 是 base Anaconda 的 `E:\Anaconda\python.exe`，不是项目要求的 `Npflower`。后续跑项目命令应继续显式使用：

```powershell
conda run -n Npflower python ...
```

> 使用npflower运行项目中代码

<details><summary>2 previous messages</summary>

> 我会按项目的 `AGENTS.md` 约定用 `conda run -n Npflower` 执行。先跑一个无副作用的帮助命令确认环境能启动项目脚本。
>
> `conda run` 在当前沙箱里被拒绝了，我按权限规则请求一次提升权限来确认 `Npflower` 能运行项目脚本。

</details>

已确认可以用 `Npflower` 运行项目代码。命令成功：

```powershell
conda run -n Npflower python 05_rq1\rq1_main.py --help
```

后续我会按这个形式运行项目脚本，例如：

```powershell
conda run -n Npflower python 01_data\data_main.py ...
conda run -n Npflower python 05_rq1\rq1_main.py ...
```

> conde-humanevalplus是code的复制，现在需要吧mbppplus数据集换成humanevalplus。确保最小改动，并且rq1成功运行，并且是一个通用模型，适配原来的mbppplus和之后的[codecontestplus](https://huggingface.co/collections/ByteDance-Seed/codecontestsplus)https://huggingface.co/collections/ByteDance-Seed/codecontestsplus

<details><summary>14 previous messages</summary>

> 我会先确认当前目录和 `conde-humanevalplus` 的位置，然后把数据加载改成适配器式：默认仍兼容 MBPPPlus，当前复制项目切到 HumanEvalPlus，同时给 CodeContestsPlus 预留适配入口。
>
> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `https://huggingface.co/collections/ByteDance-Seed/codecontestsplus`
> - Searched the web for `https://huggingface.co/datasets/ByteDance-Seed/Code-Contests-Plus`
>
> </details>
>
> </details>
>
> 我确认到复制目录是 `F:\Pycharm2023\CodeMutation\code-humanevalplus`。CodeContestsPlus 不是函数题格式，HuggingFace 页面显示它是竞赛题，字段包含 `description`、`correct_submissions`、`incorrect_submissions`，并有 `default/1x/2x...` 子集；所以我会先把框架做成通用适配器，但当前只启用 `mbppplus/humanevalplus` 的函数调用流，CodeContestsPlus 留出明确的 `stdio` 扩展口。
>
> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `evalplus/humanevalplus Hugging Face dataset`
> - Searched the web for `site:huggingface.co/datasets/ByteDance-Seed CodeContestsPlus description correct_submissions incorrect_submissions`
>
> </details>
>
> </details>
>
> 我准备改三个点：`01_data` 增加数据集适配器并默认 HumanEvalPlus；`03_splice` 优先使用 `meta.json` 的 `entry_point`；`paths/config1` 改到 `output_humanevalplus`，这样 RQ1/RQ2 不用改。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_utils.py` (+254 -96)
>
> </details>
>
> `01_data` 已经变成适配器入口：当前复制项目默认加载 HumanEvalPlus，但仍可以通过 `--dataset mbppplus` 生成原 MBPPPlus 格式；CodeContestsPlus 先给出明确的适配异常，避免静默生成错误任务。接下来我把 CLI 和函数名读取补齐。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_main.py` (+18 -11)
>
> </details>
>
> 下一步是让 `03_splice` 读 `meta.json` 的 `entry_point`。这不改变 RQ1/RQ2 接口，只是让 HumanEvalPlus 的函数入口更稳定。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/03_splice/splice_utils.py` (+25 -11)
>
> </details>
>
> 现在把复制项目的默认目录从 MBPPPlus 切到 HumanEvalPlus；变量名暂时保留 `MBPP_DIR`，这样下游代码不用跟着改。
>
> <details><summary>Edited 2 files</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/paths.py` (+3 -3)
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/config1.json` (+6 -6)
>
> </details>
>
> 改动已经完成到最小可运行形态。接下来我用 `Npflower` 做语法检查和小样本数据生成，验证 RQ1 前置文件能正常产出。
>
> 语法检查通过。现在尝试生成 5 个 HumanEvalPlus 任务；如果本机没有缓存或需要联网，我会按沙箱规则请求联网/外部权限。

</details>

HumanEvalPlus 真实下载这一步被网络/DNS 阻断了，`Npflower` 里也没有安装 `evalplus` 包，所以不能现场拉取数据集。我会继续用一个 HumanEvalPlus 结构的本地假样本验证生成文件、splice 和本地执行链路，确认代码路径本身没问题。

> 继续

<details><summary>16 previous messages</summary>

> 我继续做本地链路验证。刚才只是 PowerShell/Python 单行字符串转义失败，不是适配代码失败；我换成不含换行转义陷阱的写法生成一个 HumanEvalPlus 结构的合成任务。
>
> 合成任务已经写出。现在我跑 `03_splice` 和 `04_local_exec` 的 original 流程，验证生成的文件能被现有 RQ1 前置链路消费。
>
> 文件结构和输入格式符合现有 MBPPPlus 流程：每行都是参数列表，目录名也已处理 `HumanEval/0` 里的斜杠。接下来跑拼接和本地执行。
>
> `sample_inputs.py` 已生成，下一步执行 original 本地结果，确认 `sample_code_results.txt` 行数和输入行一致。
>
> 本地执行成功。现在我读取输出结果并做一次 MBPPPlus 兼容 smoke：用同一适配器命令生成一个 MBPPPlus 小样本到临时目录，确保原数据集入口没有被破坏。
>
> 明白，我不再做 MBPPPlus 兼容检查。现在直接拉 HumanEvalPlus，并用真实数据做小规模生成、拼接、本地执行测试。
>
> <details><summary>Searched the web</summary>
>
> <details><summary>Searched the web</summary>
>
> - Searched the web for `huggingface evalplus humanevalplus dataset`
>
> </details>
>
> </details>
>
> 我先确认 `Npflower` 里是否已有 `evalplus` 或 HuggingFace 缓存；如果没有，就尝试直接下载真实 HumanEvalPlus。
>
> 真实 HuggingFace `evalplus/humanevalplus` 已下载成功，字段和我之前按 EvalPlus 包推断的不完全一样：当前 HF 版本是 `task_id/prompt/canonical_solution/entry_point/test`。我现在检查 `test` 字段格式并调整适配器。
>
> `test` 里仍然包含 `inputs = [...]` 和 `results = [...]`，只是包在 `check(candidate)` 函数内部，且调用形式是 `candidate(*inp)`。我把 HumanEvalPlus 适配器改成优先从 `test` 提取真实输入，不依赖不存在的 `base_input/plus_input`。
>
> 还需要修正 `combined.py` 的生成：HumanEvalPlus 原始测试使用 `candidate(*inp)`，项目需要直接调用真实函数名。数据准备阶段生成 `combined.py` 不是 RQ1 核心，但保持一致更稳。
>
> 我会直接修正适配器，不再需要额外查看数据。修正后重新用真实 HumanEvalPlus 生成 5 个任务并跑 original 小规模测试。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_utils.py` (+20 -13)
>
> </details>
>
> `combined.py` 这个改动可以做到对 MBPPPlus 零影响：只把 HumanEvalPlus 测试里的 `candidate(` 替换成真实 `entry_point(`。MBPPPlus 的测试本来就是 `assertion(真实函数名(*inp), exp, 0)`，不包含 `candidate(`，所以不会被改写。我会再把这个逻辑收紧成显式兼容写法，避免以后误伤。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_utils.py` (+1 -1)
>
> </details>
>
> 现在逻辑已经收紧：只有表达式里真的出现 `candidate(` 才替换。这样 MBPPPlus 原始格式会原样保留，HumanEvalPlus 才做必要转换。

</details>

可以，`combined.py` 的改法不会破坏原来的 MBPPPlus。

现在逻辑是：

```python
if entry_point and "candidate(" in expression:
    expression = expression.replace("candidate(", f"{entry_point}(")
```

含义：

- HumanEvalPlus 的测试通常是 `assertion(candidate(*inp), exp, atol)`，会被改成 `assertion(has_close_elements(*inp), exp, atol)`。
- MBPPPlus 原来就是 `assertion(next_smallest_palindrome(*inp), exp, 0)`，没有 `candidate(`，所以完全不变。
- 这是最小兼容改动，不需要为 MBPPPlus 单独分支。

所以同一套 `01_data/data_utils.py` 可以继续支持：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset humanevalplus ...
conda run -n Npflower python 01_data\data_main.py --dataset mbppplus ...
```

当前 `code-humanevalplus` 默认是 HumanEvalPlus；如果以后把这套改回主项目，也可以通过 `--dataset` 选择数据集。

> 现在测试一下rq1及其前置任务，02,03,04,05的运行和结果分析

<details><summary>23 previous messages</summary>

> 我会用真实 HumanEvalPlus 小样本跑完整前置链路：先刷新 `01_data` 的 5 个任务，然后跑 `02_mutation` 的等价/非等价 smoke、`03_splice`、`04_local_exec`、`05_validate/RQ1 evaluate`。如果 02 或 RQ1 run 需要 API key 而本机没有配置，我会把失败点和已验证到的文件链路分开说明。
>
> `02_mutation` 是在线 LLM 变异步骤，会读取 `config1.json` 里的 API key；如果 `${YUNWU_API_KEY}` 没有实际环境变量，02 会失败。先从真实 HumanEvalPlus 数据生成 5 个任务，并检查文件格式。
>
> 真实数据 5 个任务已生成。下一步跑 `03_splice --mode original` 和 `04_local_exec --mode original`，这是 RQ1 准确性的基础：同一批 sample 输入要能本地执行得到基准结果。
>
> 我发现真实 HumanEvalPlus 暴露了两个需要修正的兼容问题：`test` 里的 `results` 行有缩进，导致输入没有被提取，旧的合成 `sample_code_inputs.txt` 残留；另外 `combined.py` 对缩进的 `assertion(...)` 处理不稳。我现在修正这两个数据准备问题，再重跑真实小样本。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_utils.py` (+21 -5)
>
> </details>
>
> 修正已经完成：输入提取允许缩进的 `results`，并且无输入时直接失败，避免复用残留文件。现在重新跑真实 5 题数据生成和检查。
>
> 数据重新生成成功。现在检查第一个任务的输入与 `combined.py`，然后跑 03/04。
>
> 输入现在是正确的真实 HumanEvalPlus 参数列表，但 `combined.py` 里 `result.append(...)` 看起来还少了一个右括号。我继续修正 assertion 表达式提取，保证生成的辅助执行文件也有效。
>
> 问题来源找到了：原来的 `process_test_field()` 会把 `assertion(candidate(*inp), exp, atol)` 按第一个 `)` 截断，这对 HumanEvalPlus 的 `candidate(*inp)` 会误删右括号。我把 assertion 行保持完整，再由 AST 提取第一个参数，生成的 `combined.py` 就会稳定。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_utils.py` (+5 -7)
>
> </details>
>
> 继续重生成真实小样本，并重新检查 `combined.py` 的关键行。
>
> 数据准备和语法检查都通过。现在执行 `combined.py` 语法检查、`03_splice`、`04_local_exec`。
>
> `combined.py` 现在有效，03 的 original 拼接也 5/5 成功。下一步跑 04 original，生成本地基准结果。
>
> 04 original 本地执行 5/5 成功，说明 RQ1 的基准结果文件可以生成。接下来测试 02 变异；这一步依赖 LLM API，我会先用 1 个任务跑等价变异看配置是否可用。
>
> 02 的等价变异 API 调用成功，说明 key/base_url 可用。现在跑非等价 1 个任务，然后拼接/执行 equivalent 与 non_equivalent，并做 05 validate。
>
> 02 的两类变异各 1 个任务都成功写出。现在对这 1 个任务跑 03/04 的 mutation 分支，并生成 non-equivalent compare 结果。
>
> 03 的 mutation 分支按预期：只有 task_HumanEval_0 有变异文件，所以 equivalent/non_equivalent 各写出 1 个，其余 4 个缺失。现在跑 04 all limit 1 和 compare。
>
> 04 三种模式本地执行都成功，但非等价变异在 3 个采样输入上结果全相同，`compare_non_equivalent` 标记为 100% invalid。这说明链路能跑，当前这次 LLM 生成的 non-equivalent 变异质量不合格，需要 05 validate 报告出来。
>
> 05 的 mutation validation 结果符合 04 的观察：equivalent 通过，non-equivalent 未通过。接下来跑 RQ1 的 LLM 执行预测 smoke：original/equivalent/non_equivalent 各 1 个任务，然后统一 evaluate。
>
> RQ1 original 的 1 个 LLM 执行预测完成。继续跑 equivalent 和 non_equivalent 的同一任务，便于一次 evaluate 汇总。
>
> RQ1 equivalent 也完成。现在跑 non_equivalent，然后评估三种模式。
>
> RQ1 smoke 已完成：original 100%，equivalent 66.67%，non_equivalent 因变异无效而没有有效 case。最后我读取关键输出文件，确认行数和报告落盘。
>
> 我已经拿到结果，最后确认一下当前变更文件列表，避免把生成文件和代码改动混在一起说明。

</details>

已用真实 `evalplus/humanevalplus` 小样本跑通 RQ1 前置链路和 RQ1 smoke。

改动集中在：
[01_data/data_utils.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_utils.py)、[01_data/data_main.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/01_data/data_main.py)、[03_splice/splice_utils.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/03_splice/splice_utils.py)、[paths.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/paths.py)、[config1.json](f:/Pycharm2023/CodeMutation/code-humanevalplus/config1.json)。

**运行结果**
`01_data`：真实 HumanEvalPlus 下载并生成 5 个任务成功。

```text
written=5, skipped=0, failed=0
```

`03_splice --mode original`：5/5 成功。

```text
Done original. written=5, missing=0
```

`04_local_exec --mode original --limit 5`：5/5 成功。

```text
Success: 5
Failed: 0
Missing: 0
Timeout: 0
```

`02_mutation`：等价/非等价各测试了 1 个任务，API 调用都成功并写出文件。

```text
equivalent: [done] task_HumanEval_0
non_equivalent: [done] task_HumanEval_0
```

`03_splice --mode all`：original 5 个都成功，mutation 分支只对已有变异文件的 task 0 成功，其余 4 个缺失是预期结果。

```text
original written=5
equivalent written=1, missing=4
non_equivalent written=1, missing=4
```

`04_local_exec --mode all --limit 1 --compare_non_equivalent`：三种模式本地执行都成功；但本次 non-equivalent 变异在 3 个采样输入上没有改变输出。

```text
original/equivalent/non_equivalent: Success 1
Non-equivalent invalid same-result cases: 3 / 3
```

`05_rq1/validate_main.py --limit 1`：

```text
equivalent: passed=1, failed=0
non_equivalent: passed=0, failed=1
reason: no_difference
```

`RQ1 run/evaluate` 使用 `output_name=humaneval_smoke`，三种模式各跑 1 个任务：

```text
original:       3 / 3, accuracy 100.00%
equivalent:     2 / 3, accuracy 66.67%
non_equivalent: no_valid_cases
```

报告已写到：
[reports/rq1_humaneval_smoke.json](f:/Pycharm2023/CodeMutation/code-humanevalplus/reports/rq1_humaneval_smoke.json)
[reports/mutation_failures.json](f:/Pycharm2023/CodeMutation/code-humanevalplus/reports/mutation_failures.json)

结论：HumanEvalPlus 数据准备、03 拼接、04 本地执行、05 验证、RQ1 run/evaluate 都能跑通。当前唯一失败点不是数据集适配，而是这次 LLM 生成的 non-equivalent 变异质量不合格，输出没有变化；可以用 `05_rq1\validate_main.py --retry --run_exec` 或重新跑 non-equivalent mutation 来修。

> 重新多跑10个看看看看，并检查一下生成文件的内容是否符合要求

<details><summary>15 previous messages</summary>

> 我会按真实 HumanEvalPlus 重新跑 10 个任务：先生成数据，再跑 02 等价/非等价变异、03 拼接、04 本地执行、05 验证，最后抽查生成文件的结构、语法和行数一致性。RQ1 LLM 执行预测我会等前置链路确认后再跑，避免在明显无效变异上浪费调用。
>
> 10 个真实任务已经生成。现在跑 02 的等价和非等价变异，各 10 个任务；这一步是在线 LLM 调用，可能会花一会儿。
>
> 等价变异 10/10 完成。继续跑非等价变异 10 个任务。
>
> 02 两类变异都生成完成。现在跑 03 全量拼接，再跑 04 三模式本地执行并构建 non-equivalent compare 文件。
>
> 03 三个模式全部 10/10 写出。现在跑 04 本地执行；这会验证生成脚本是否真的可运行。
>
> 04 结果里 original/equivalent 都 10/10 成功，non-equivalent 有 1 个生成代码运行时错误（task_HumanEval_9），另外 9 个可比较任务里有 6/27 个采样 case 仍然输出相同。现在跑 05 验证，并做文件内容/结构检查。
>
> 验证报告已经出来：等价变异 10/10 通过；非等价变异 7/10 通过，task 0、3、9 有问题，其中 task 9 是本地执行失败导致结果文件缺失。现在我用脚本检查目录结构、关键文件、Python 语法、输入/结果行数一致性，以及 `combined.py` 是否还有 `candidate(` 或截断痕迹。
>
> 刚才的完整性检查命令只输出了第一行，PowerShell/`python -c` 的换行传递被截断了。我换成 `exec(...)` 单行形式重新跑同一套检查。
>
> 完整性检查的长命令被 PowerShell 引号解析拦住了。我拆成几个简单检查来做：递归编译所有生成的 Python 文件、查 `combined.py` 中的异常 token、统计各任务输入和结果行数。
>
> 递归编译通过，说明生成的 Python 文件语法都合法。刚才 `ion(` 的模糊搜索误匹配到了 `deviation(`，我会用更精确的词边界再查一次，并做行数统计。
>
> 文件检查结果：10 个变异文件都存在；original/equivalent 的输入和结果行数全部一致；non-equivalent 的 task 9 因运行时错误缺少结果和 compare 文件。现在继续跑 RQ1 的 10 题 smoke，使用 `output_name=humaneval_10`。
>
> RQ1 original 10/10 已完成。继续跑 equivalent 10/10。
>
> RQ1 equivalent 10/10 已完成。继续跑 non-equivalent；注意 task 9 的本地结果缺失，后续 evaluate 会把它列为 missing-file。
>
> 三种 RQ1 LLM 输出都已生成。现在跑统一 evaluate 并写报告。
>
> RQ1 10 题评估完成。最后我抽查 LLM 输出文件行数和报告内容，并看一下失败/无效任务对应的文件内容。

</details>

已重新跑 10 个真实 HumanEvalPlus 任务，并检查生成文件内容。

**前置链路结果**

`01_data`：

```text
HumanEvalPlus 10/10 written
```

`02_mutation`：

```text
equivalent: 10/10 done
non_equivalent: 10/10 done
```

`03_splice`：

```text
original:       written=10, missing=0
equivalent:     written=10, missing=0
non_equivalent: written=10, missing=0
```

`04_local_exec`：

```text
original:       success=10, failed=0
equivalent:     success=10, failed=0
non_equivalent: success=9, failed=1
```

`05_validate`：

```text
equivalent:     passed=10, failed=0, missing=0
non_equivalent: passed=7, failed=3, missing=1
```

失败点是 non-equivalent 变异质量，不是 HumanEvalPlus 数据适配问题：

```text
task_HumanEval_0: no_difference
task_HumanEval_3: no_difference
task_HumanEval_9: missing_result
```

`task_HumanEval_9` 的非等价变异代码运行时报错，原因是它生成了：

```python
return [max(numbers[:(i-1)]) for i in range(len(numbers))]
```

当 `i=0` 时切片为空，`max([])` 抛 `ValueError`，所以没有生成 `sample_code_results_non_equivalent.txt`。

**生成文件检查**

已检查：

```text
output_humanevalplus
equivalent_transform_humanevalplus
non_equivalent_transform_humanevalplus
```

结果：

```text
Python 递归编译通过
combined.py 无 candidate( 残留
combined.py 无截断 ion( 问题
equivalent transform 文件数: 10
non_equivalent transform 文件数: 10
```

行数一致性：

```text
task_HumanEval_0..8:
  inputs=3
  original=3
  equivalent=3
  non_equiv=3
  compare=3

task_HumanEval_9:
  inputs=3
  original=3
  equivalent=3
  non_equiv=missing
  compare=missing
```

**RQ1 10 题结果**

已跑：

```text
output_name = humaneval_10
```

三种模式的 LLM 输出文件都是 10 个：

```text
sample_output_LLMs_original_code/humaneval_10: 10
sample_output_LLMs_equivalent_code/humaneval_10: 10
sample_output_LLMs_non_equivalent_code/humaneval_10: 10
```

评估结果：

```text
original:
  valid tasks: 10
  same cases: 20 / 30
  accuracy: 66.67%

equivalent:
  valid tasks: 10
  same cases: 20 / 30
  accuracy: 66.67%

non_equivalent:
  valid tasks: 7
  same cases: 12 / 21
  accuracy: 57.14%
  missing-file tasks: 1
  no-valid-case tasks: 2
```

报告已写入：

[reports/rq1_humaneval_10.json](f:/Pycharm2023/CodeMutation/code-humanevalplus/reports/rq1_humaneval_10.json)
[reports/mutation_failures.json](f:/Pycharm2023/CodeMutation/code-humanevalplus/reports/mutation_failures.json)

结论：HumanEvalPlus 的数据生成、拼接、本地执行、RQ1 运行和评估都能工作。当前主要问题是 non-equivalent LLM 变异质量不稳定，10 个里 3 个不合格，其中 1 个会运行时崩溃。

> 你的目标是保证数据集不做变异的原始代码100%运行，保证生产的非等价和等价代码的正确运行，然后运行rq1.先告诉我刚才的10个测试用例结果如何

刚才 10 个 HumanEvalPlus 小规模测试结果如下。

**原始代码**
`01_data -> 03_splice original -> 04_local_exec original`：

```text
10 / 10 成功运行
failed=0
missing=0
timeout=0
```

也就是说，**不做变异的原始代码 100% 可以运行**。

**等价变异代码**
`02 equivalent -> 03_splice equivalent -> 04_local_exec equivalent -> 05_validate`：

```text
生成: 10 / 10
本地运行: 10 / 10 成功
验证: 10 / 10 passed
```

也就是说，**等价变异代码 100% 正确运行，并且行为验证通过**。

**非等价变异代码**
`02 non_equivalent -> 03_splice non_equivalent -> 04_local_exec non_equivalent -> 05_validate`：

```text
生成: 10 / 10
本地运行: 9 / 10 成功
本地运行失败: task_HumanEval_9
验证通过: 7 / 10
验证失败: task_HumanEval_0, task_HumanEval_3, task_HumanEval_9
```

失败原因：

```text
task_HumanEval_0: no_difference，变异后输出和原始输出相同
task_HumanEval_3: no_difference，变异后输出和原始输出相同
task_HumanEval_9: 运行时报错，未生成 non_equivalent 结果文件
```

`task_HumanEval_9` 的错误是非等价变异代码生成了：

```python
return [max(numbers[:(i-1)]) for i in range(len(numbers))]
```

当 `i=0` 时 `max([])` 抛异常。

**RQ1 结果**
在上述数据上跑了 `rq1_main.py run/evaluate`，`output_name=humaneval_10`。

```text
original:
  10 个任务有效
  20 / 30 case 匹配
  accuracy = 66.67%

equivalent:
  10 个任务有效
  20 / 30 case 匹配
  accuracy = 66.67%

non_equivalent:
  7 个任务有效
  12 / 21 case 匹配
  accuracy = 57.14%
  missing-file tasks = 1
  no-valid-case tasks = 2
```

结论：**原始代码和等价变异已经满足目标；非等价变异还没满足目标**。需要先把 non-equivalent 的失败任务重新生成/修复，直到本地运行成功且验证通过，再正式跑 RQ1。

> 给我一个解决方案，现在可以全量数据集测试吗

现在**不建议直接全量跑 RQ1**。原因不是 HumanEvalPlus 数据集适配问题，而是 **non-equivalent 变异质量还没有稳定达标**。刚才 10 个里：

```text
原始代码运行: 10/10
等价变异运行+验证: 10/10
非等价变异运行: 9/10
非等价变异验证: 7/10
```

如果现在全量跑，RQ1 的 `non_equivalent` 会混入无效任务、缺失结果和运行时报错任务，最终报告会低估或污染结论。

**解决方案**

目标应该分成两层：

```text
第一层：数据集适配和原始代码 100% 可运行
第二层：等价/非等价变异通过本地验证后，再进入 RQ1
```

当前第一层已基本通过；第二层需要加一个筛选/重试机制。

**方案 1：先全量验证原始代码**

可以马上全量跑这部分，成本低且应该先做：

```powershell
conda run -n Npflower python 01_data\data_main.py --dataset humanevalplus --sample_size 3 --seed 0 --overwrite
conda run -n Npflower python 03_splice\splice_main.py --mode original
conda run -n Npflower python 04_local_exec\exec_main.py --mode original --timeout 30
```

目标：

```text
original success = 164 / 164
```

如果原始代码不是 100%，先修数据适配；不要继续变异。

**方案 2：全量生成等价/非等价，但不直接进 RQ1**

跑：

```powershell
conda run -n Npflower python 02_mutation\mutation_main.py --mode equivalent --max_workers 2 --overwrite
conda run -n Npflower python 02_mutation\mutation_main.py --mode non_equivalent --max_workers 2 --overwrite

conda run -n Npflower python 03_splice\splice_main.py --mode all
conda run -n Npflower python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent

conda run -n Npflower python 05_rq1\validate_main.py
```

然后只允许这些任务进入 RQ1：

```text
original local result exists
equivalent local result exists
non_equivalent compare result exists
equivalent validation passed
non_equivalent validation passed
```

**方案 3：对失败 non-equivalent 自动重试**

已有脚本支持 retry，可以先试：

```powershell
conda run -n Npflower python 05_rq1\validate_main.py --retry --run_exec --include_missing --overwrite
```

但我建议改进 prompt 或重试策略，否则像 `max([])` 这种运行时错误可能继续出现。

非等价变异 prompt 需要增加硬约束：

```text
- The mutated program must not raise exceptions for any provided sample input.
- Do not mutate list slice bounds or loop bounds in a way that can create empty max/min calls.
- The mutation must change output for at least one sampled input.
- Preserve input/output type and function signature.
```

更稳的做法是把失败样例输入也喂给 retry prompt，让 LLM 必须生成能在这些输入上运行且至少一个输出不同的代码。

**推荐正式流程**

我建议你现在这样推进：

1. 先全量跑原始代码，确认 `164/164`。
2. 全量跑 equivalent，要求本地运行和 validate 都接近 `100%`。
3. 全量跑 non-equivalent。
4. 对 non-equivalent 失败任务循环 retry，直到：
   ```text
   no missing result
   no runtime error
   no no_difference
   ```
5. 只对通过 validation 的任务跑 RQ1。
6. RQ1 报告里明确记录：
   ```text
   dataset_total
   original_runnable
   equivalent_valid
   non_equivalent_valid
   rq1_evaluated
   ```

**是否现在可以全量测试？**

可以全量测试 **数据准备和原始代码运行**：

```text
可以，现在就跑。
```

不建议现在全量跑 **RQ1 final**：

```text
不建议，non-equivalent 还没有过滤干净。
```

可以全量跑 **RQ1 smoke/precheck**，但不能把结果当最终实验结果。最终 RQ1 必须基于 validation-passed 的任务集。

> 请解决non-equivalent 变异质量还没有稳定达标的问题，注意保证最小修改，原来的数据集和现在的都能用，为啥原来的可以跑，现在的不行

<details><summary>32 previous messages</summary>

> 我先看 `05_rq1/validate_utils.py` 里已有的 retry 机制和 `02_mutation` 的 prompt 入口。目标是只改 prompt/重试上下文这类低侵入点，不改 RQ1 评估逻辑，也不破坏 MBPPPlus。
>
> 原因很明确：原来的 MBPPPlus 多数函数和测试输入比较简单，generic “改一个 operator/literal” 往往既能运行又容易改变输出；HumanEvalPlus 的输入更偏边界和类型压力测试，像 list slicing、空列表、阈值浮点、排序类函数更多，随手改一个边界或比较符更容易造成两类问题：要么 sampled inputs 上输出没变，要么触发运行时异常。解决点不应该在 RQ1，而应该在 02 的非等价生成 prompt 和 05 的失败重试 prompt 上加“样例输入感知”和“必须可运行”的约束。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py` (+40 -11)
>
> </details>
>
> 我已让 02 变异生成能读取每个任务的 `sample_code_inputs.txt` 和已存在的 original 结果。这个改动是向后兼容的：旧 prompt builder 仍可只接收 code，不会破坏 MBPPPlus。接下来收紧非等价 prompt。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_utils.py` (+40 -20)
>
> </details>
>
> 非等价初始生成现在会看到 sampled inputs 和 original outputs，并被明确要求“这些输入上必须可运行，且至少一个输出不同”。下一步加强 05 retry，使 missing_result 这类运行崩溃也带着样例输入/输出重试。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/05_rq1/validate_utils.py` (+33 -27)
>
> </details>
>
> 05 retry prompt 也已补强，运行崩溃的 missing_result 会带上 original 样例输出再生成。现在先语法检查，再只重跑 non-equivalent 的 10 个任务，验证是否改善。
>
> 语法检查通过。现在按目标流程重跑：先确保 original 结果已存在，再用新 prompt 重新生成 10 个 non-equivalent，拼接、执行、验证。
>
> 新的 non-equivalent 10/10 已生成。现在重新拼接 non-equivalent、执行并 compare。
>
> 我看到新 prompt 后 `task_HumanEval_9` 仍然生成了同样的危险切片，说明只靠 prompt 不够。最小可靠修复是：02 生成代码时就用当前 sampled inputs 做一次本地快速验证，非等价必须“能运行且至少一个输出不同”才写入文件；否则自动再问 LLM。这样原 MBPPPlus 也受益，且不动 RQ1。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py` (+82 -28)
>
> </details>
>
> 我还需要防止一种隐患：如果 `--overwrite` 后连续候选都不合格，旧的坏文件不能继续留着。现在加一行，在覆盖模式下先移除旧输出，避免 stale mutation 被后续步骤误用。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py` (+7 -5)
>
> </details>
>
> 现在 02 会拒绝运行时报错或没改变 sampled outputs 的非等价代码，并自动最多尝试 3 个候选。接下来语法检查并重跑 10 个 non-equivalent 验证效果。
>
> 语法检查通过。现在重跑 10 个 non-equivalent。你会看到被拒绝的候选会打印 `[invalid] ... candidate=...`，只有通过 sampled validation 的才会写文件。
>
> 现在本地验证挡住了坏变异，但 task 0 和 task 9 的 LLM 连续 3 次仍没给出合格代码。为了解决稳定性，我加一个确定性 fallback：LLM 候选都失败时，对原始 AST 做单点变异，逐个在 sampled inputs 上本地验证；只有“可运行且输出不同”的候选才写入。这个 fallback 对 MBPPPlus 和 HumanEvalPlus 都通用。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py` (+96 -0)
>
> </details>
>
> 我发现 transformer 里可以更严格地保证“只做一个单点变异”，我把命中目标后直接返回该节点，避免继续遍历同一个节点造成额外改动。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py` (+3 -3)
>
> </details>
>
> 现在 fallback 保证只做一个 AST 级别的单点变异，并且仍用 sampled inputs 验证。接下来语法检查，再重跑 10 个 non-equivalent。
>
> Fallback 暴露了一个实现 bug：我收集 mutation 点用的是 `ast.walk`，实际替换用的是 NodeTransformer 的遍历顺序，两者顺序不一致，导致某个 replacement index 越界。这个是代码问题，不是数据问题。我会把收集和替换统一成同一种 AST 前序遍历，并让并发任务异常不会把整个批次直接打断。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py` (+20 -8)
>
> </details>
>
> 遍历顺序已统一，并发 worker 也会报告错误而不是中断整个批次。现在重新跑语法检查和 non-equivalent 10 题生成。
>
> 这次 10/10 都成功生成，其中 task 0、3、9 走了确定性 fallback。现在重新拼接、执行 non-equivalent、compare、validate。
>
> 拼接成功。继续执行 non-equivalent 并生成 compare。
>
> non-equivalent 现在 10/10 可运行，且没有整题完全相同；仍有 2/30 个单独 case 相同，这在当前验证标准下是可接受的，因为每个任务至少有一个 case 改变。现在跑 05 validation。
>
> 目标达成：10 个任务里等价和非等价都 10/10 通过验证。现在我检查生成文件行数和 fallback 变异内容，确认没有运行结果缺失。
>
> 验证报告现在干净：equivalent/non-equivalent 都 10/10 通过，所有结果文件行数一致。由于 non-equivalent 代码已经更新，之前的 RQ1 non-equivalent 输出不再对应当前代码；我重新跑 `humaneval_10_fixed` 三个模式，得到一致的 RQ1 报告。
>
> RQ1 original 10/10 已重跑完成。继续重跑 equivalent。
>
> RQ1 equivalent 10/10 已完成。继续重跑 non-equivalent。
>
> 三种 RQ1 输出已全部重跑。现在生成最终 evaluate 报告。

</details>

已解决 10 个样本里的 non-equivalent 稳定性问题，并重新跑了 RQ1。

原因总结：原 MBPPPlus 更简单，generic prompt 改一个 operator/literal 通常能运行并改变输出；HumanEvalPlus 有更多边界输入、浮点阈值、列表切片/滚动窗口类代码，LLM 容易生成“运行时报错”或“采样输入上输出没变”的非等价代码。

我做的最小修改：

- [02_mutation/mutation_runner.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_runner.py)：生成变异后，立刻用 `sample_code_inputs.txt` 和原始结果做本地校验。
  - equivalent：必须 sampled outputs 全相同。
  - non-equivalent：必须无异常运行，且至少一个 sampled output 不同。
  - LLM 连续失败后，对 non-equivalent 启用 AST 单点变异 fallback。
- [02_mutation/mutation_utils.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/02_mutation/mutation_utils.py)：非等价 prompt 加入 sampled inputs/original outputs 和“不允许异常”的约束。
- [05_rq1/validate_utils.py](f:/Pycharm2023/CodeMutation/code-humanevalplus/05_rq1/validate_utils.py)：missing-result 的 retry 也带上样例输入/输出。

这些改动是通用的，MBPPPlus 也能用；如果原始结果文件不存在，会自动跳过 sample 行为校验，不破坏旧流程。但推荐流程是先跑 original，再跑 mutation。

修复后 10 个样本结果：

```text
original local exec:       10/10 success
equivalent validation:     10/10 passed
non_equivalent validation: 10/10 passed
```

non-equivalent compare：

```text
Tasks: 10
Invalid same-result cases: 2 / 30
Fully same tasks: 0
```

这表示每个 non-equivalent 任务至少有一个 sampled case 改变输出，满足当前验证标准；个别 case 相同是允许的。

重新跑 RQ1，`output_name=humaneval_10_fixed`：

```text
original:
  18 / 30, accuracy 60.00%

equivalent:
  19 / 30, accuracy 63.33%

non_equivalent:
  16 / 28, accuracy 57.14%
  missing-file tasks: 0
  no-valid-case tasks: 0
```

报告在：

[reports/rq1_humaneval_10_fixed.json](f:/Pycharm2023/CodeMutation/code-humanevalplus/reports/rq1_humaneval_10_fixed.json)

现在可以进入全量测试，但建议按阶段跑：先全量 original，确认 164/164；再全量 equivalent/non-equivalent；再 validate，只有验证全通过后跑最终 RQ1。

> 删除reports无关的报告

<details><summary>3 previous messages</summary>

> 我先看当前工作区 `reports` 里有哪些文件，确认哪些像是临时/无关报告；删除前会只针对明显的 smoke/旧结果文件，不碰代码和主数据。
>
> 当前 `code/reports` 里只有两个 Git 未跟踪的新报告看起来是无关临时文件：`non_equiv_363_wrong_not_pre_answer_20260617.*`。我只删除这两个，不碰已有的 final/recheck/README 报告。
>
> 删除已完成。我再确认 `reports` 和 Git 状态，确保只删了那两个临时文件。

</details>

已删除 `code/reports` 下两个无关临时报告：

```text
non_equiv_363_wrong_not_pre_answer_20260617.json
non_equiv_363_wrong_not_pre_answer_report_20260617.md
```

保留了已有 final/recheck/README 报告。当前 `git status` 干净。

> 目前操作目录是啥

当前操作目录是：

```text
f:\Pycharm2023\CodeMutation\code
```

> 为啥不是F:\Pycharm2023\CodeMutation\code-humanevalplus

因为这次新的 `environment_context` 把工作区根目录切回了：

```text
f:\Pycharm2023\CodeMutation\code
```

所以我刚才默认在 `code` 里操作了。之前 HumanEvalPlus 的工作是在复制目录：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus
```

如果你要继续处理 HumanEvalPlus 项目，我后续会显式把命令的 `workdir` 设为：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus
```

> 你操作失误了，删除了不该删除的

<details><summary>2 previous messages</summary>

> 你说得对，这是我的失误：我没有在删除前再次确认目标目录，误在 `code` 而不是 `code-humanevalplus` 下删除了两个报告。我现在先尽最大可能查找是否有副本或可恢复来源。
>
> <details><summary>Ran 4 commands</summary>
>
> - Ran `git status --short`
> - Ran `Get-ChildItem -Path F:\Pycharm2023\CodeMutation -Recurse -Force -Filter 'non_equiv_363_wrong_not_pre_answer_20260617*' | Select-Object FullName,Length,LastWriteTime`
> - Ran `git ls-files --stage -- reports/non_equiv_363_wrong_not_pre_answer_20260617.json reports/non_equiv_363_wrong_not_pre_answer_report_20260617.md`
> - Ran `Get-ChildItem -Path F:\Pycharm2023\CodeMutation\code\reports -Force | Select-Object Name,Length,LastWriteTime`
>
> </details>

</details>

你说得对，我刚才操作目录判断错了，应该先确认是否要处理 `code-humanevalplus`，不该直接删 `code/reports`。

我刚检查了一遍，目前这两个文件已经在 `F:\Pycharm2023\CodeMutation\code\reports` 下存在：

```text
non_equiv_363_wrong_not_pre_answer_20260617.json
non_equiv_363_wrong_not_pre_answer_report_20260617.md
```

`git status` 也显示它们是未跟踪文件：

```text
?? reports/non_equiv_363_wrong_not_pre_answer_20260617.json
?? reports/non_equiv_363_wrong_not_pre_answer_report_20260617.md
```

所以当前看起来没有继续丢失。后续我会固定使用：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus
```

并且涉及删除操作时先列出目标文件让你确认。

> environment_context在哪里

`environment_context` 是系统/运行环境发给我的上下文信息，不是项目里的某个普通文件。

你这次发来的上下文里写的是：

```text
<cwd / workspace root>
f:\Pycharm2023\CodeMutation\code
```

所以我默认命令工作目录回到了：

```text
F:\Pycharm2023\CodeMutation\code
```

它通常会出现在对话消息里，类似：

```xml
<environment_context>
  <current_date>2026-06-17</current_date>
  <timezone>Asia/Shanghai</timezone>
  <filesystem>
    <workspace_roots>
      <root>f:\Pycharm2023\CodeMutation\code</root>
    </workspace_roots>
  </filesystem>
</environment_context>
```

它不是 `AGENTS.md`，也不是 repo 配置文件。后续如果你要我在 `code-humanevalplus` 操作，我会显式指定 `workdir` 为：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus
```

> 把他写进agnets里面，运行之前确认

<details><summary>4 previous messages</summary>

> 我会把“运行或删除前必须确认目标工作目录，尤其区分 `code` 和 `code-humanevalplus`”写进当前 `AGENTS.md`。如果还需要写到 `code-humanevalplus` 的 AGENTS，我会单独请求权限，因为它不在当前可写根目录内。
>
> <details><summary>Ran a command</summary>
>
> - Ran `Get-Content -Path AGENTS.md`
>
> </details>
>
> 我现在只改 `F:\Pycharm2023\CodeMutation\code\AGENTS.md`，加入运行/删除前的目录确认规则。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `./AGENTS.md` (+9 -0)
>
> </details>

</details>

> 你为啥还在code改。我要你在F:\Pycharm2023\CodeMutation\code-humanevalplus

<details><summary>12 previous messages</summary>

> 你说得对，我又改错目录了。现在我会先撤回 `F:\Pycharm2023\CodeMutation\code\AGENTS.md` 里刚加的那段，然后把同样规则写到 `F:\Pycharm2023\CodeMutation\code-humanevalplus\AGENTS.md`。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `./AGENTS.md` (+0 -9)
>
> </details>
>
> `code\AGENTS.md` 里的错误追加已撤回。接下来我只针对 `code-humanevalplus` 目录操作，并先读取它的 `AGENTS.md`。
>
> <details><summary>Ran a command</summary>
>
> - Ran `Get-Content -Path AGENTS.md`
>
> </details>
>
> 现在目标文件确认是 `F:\Pycharm2023\CodeMutation\code-humanevalplus\AGENTS.md`。我会把运行/删除前确认目录的规则写到这个文件。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `F:/Pycharm2023/CodeMutation/code-humanevalplus/AGENTS.md` (+15 -7)
>
> </details>
>
> 补丁没匹配上，我先重新读取完整文件尾部，确认格式后再改。
>
> <details><summary>Ran a command</summary>
>
> - Ran `Get-Content -Path AGENTS.md -Raw`
>
> </details>
>
> `code-humanevalplus\AGENTS.md` 原文件本身缺少代码块结尾，我会补上结尾并追加目录确认规则。
>
> <details><summary>Edited a file</summary>
>
> - Wrote `F:/Pycharm2023/CodeMutation/code-humanevalplus/AGENTS.md` (+12 -3)
>
> </details>
>
> `code-humanevalplus\AGENTS.md` 已更新。我再确认两个目录的状态：`code` 不应保留刚才那段，`code-humanevalplus` 应包含新规则。
>
> <details><summary>Ran 4 commands</summary>
>
> - Ran `Get-Content -Path AGENTS.md -Raw`
> - Ran `git status --short`
> - Ran `git status --short`
> - Ran `Get-Content -Path AGENTS.md -Raw`
>
> </details>

</details>

你说得对，我刚才又先碰了 `code`，这是错误操作。我已经把 `code\AGENTS.md` 里的错误追加撤回了。

现在已正确更新：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus\AGENTS.md
```

新增规则内容是：运行项目命令或删除文件前，必须在用户可见更新里确认目标目录，并显式设置 `workdir` 为：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus
```

同时要求删除报告这类破坏性操作前，先列出精确目标文件并确认它们位于 `code-humanevalplus`。

注意：`code-humanevalplus` 当前 `git status` 还显示已有工作区变化：

```text
D code.code-workspace
?? code-humanevalplus.code-workspace
```

这些不是我这一步改的 `AGENTS.md` 内容。

> 告诉我你的工作路径是什么

当前系统给我的默认工作区仍是：

```text
F:\Pycharm2023\CodeMutation\code
```

但按你的要求，后续我应该操作的项目路径是：

```text
F:\Pycharm2023\CodeMutation\code-humanevalplus
```

我之后涉及命令或文件操作时会显式使用 `workdir=F:\Pycharm2023\CodeMutation\code-humanevalplus`，并先在回复里确认目标目录。

> 把这个对话复制到另一个codex项目可以吗

可以，但不要直接复制整段长对话，容易把错误操作和过期上下文一起带过去。更好的方式是复制一份“交接摘要”。

你可以在另一个 Codex 项目里粘贴下面这段：

```text
项目目标目录是：
F:\Pycharm2023\CodeMutation\code-humanevalplus

重要规则：
1. 所有命令运行前必须确认目标目录是 code-humanevalplus。
2. 所有 shell/tool 调用必须显式设置 workdir=F:\Pycharm2023\CodeMutation\code-humanevalplus。
3. 不要误用 environment_context 里的 F:\Pycharm2023\CodeMutation\code。
4. 删除报告或文件前，必须先列出精确目标文件并确认它们位于 code-humanevalplus。
5. Python 命令使用：
   conda run -n Npflower python ...

当前已做的关键改动：
- HumanEvalPlus 已适配为当前 MBPPPlus 风格任务目录。
- 01_data 支持 --dataset humanevalplus / mbppplus / codecontestplus 占位。
- paths.py 中默认任务目录改为 output_humanevalplus。
- config1.json input_paths 改为 output_humanevalplus。
- 03_splice 优先读取 meta.json 的 entry_point。
- 02_mutation 对 generated mutation 加入 sampled input 本地校验。
- non-equivalent 生成失败时加入 AST 单点变异 fallback。
- 05_rq1 validate retry 对 missing_result 带样例输入/输出。

最近 10 个 HumanEvalPlus 测试结果：
- original local exec: 10/10 success
- equivalent validation: 10/10 passed
- non_equivalent validation: 10/10 passed
- RQ1 report: reports/rq1_humaneval_10_fixed.json

注意：
之前曾误在 F:\Pycharm2023\CodeMutation\code 操作过，后续必须固定 code-humanevalplus。
```

如果你要完整上下文，也可以复制整个对话，但建议在新项目开头明确写：

```text
忽略对话中误操作 F:\Pycharm2023\CodeMutation\code 的部分；真实目标目录是 F:\Pycharm2023\CodeMutation\code-humanevalplus。
```

> 深度链接是什么

深度链接（deep link）就是**直接跳到某个应用、页面、功能或具体内容的链接**，而不是只打开首页。

例子：

```text
普通链接：
https://example.com

深度链接：
https://example.com/orders/123
```

第一个只到网站首页；第二个直接打开订单 `123`。

在应用里也常见：

```text
myapp://product/42
```

点击后不是打开浏览器首页，而是直接打开 App 里的商品 `42` 页面。

在 Codex/GitHub/文件环境里，“深度链接”也可以指直接定位到具体资源的链接，比如：

```text
F:\project\file.py:120
```

意思是直接打开某个文件的第 120 行。
