# 代码语义等价性分析项目方法流程

## 项目概述

本项目实现了一套基于变异性测试(Mutation Testing)的代码语义等价性分析框架，通过动态分析技术验证原始代码与变异代码(通过LLM生成)的语义一致性。项目从**执行结果**和**变量变化序列**两个维度进行综合评估。

## 完整方法流程

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              完整方法流程                                            │
└─────────────────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐     ┌──────────────────┐     ┌───────────────────────┐
     │  数据集加载   │────▶│   代码变异生成    │────▶│   本地运行收集结果    │
     │ load_dataset │     │ equivalent_      │     │ run_code             │
     │              │     │ transform        │     │                      │
     └──────────────┘     └──────────────────┘     └───────────┬───────────┘
                                                                   │
                                                                   ▼
     ┌──────────────┐     ┌──────────────────┐     ┌───────────────────────┐
     │ 变量序列一致性│◀────│ LLM变量序列获取  │◀────│ 本地动态插桩获取     │
     │evaluate_trace│     │ run_llm_tracer   │     │ run_tracer           │
     └──────────────┘     └──────────────────┘     └───────────┬───────────┘
                                                                   │
                                                                   ▼
     ┌──────────────┐     ┌──────────────────┐     ┌───────────────────────┐
     │   结果评估    │◀────│  LLM输出获取      │◀────│   输出对比提取        │
     │ evaluate     │     │ run_tasks        │     │ splice_main_and_     │
     └──────────────┘     └──────────────────┘     │ function             │
                                                   └───────────────────────┘
```

---

## 详细流程说明

### 阶段一：数据集加载与预处理

**入口文件**: `load_dataset.py`

**功能**:
1. 从 HuggingFace 加载 evalplus/mbppplus 数据集
2. 为每个任务创建独立的文件夹结构
3. 生成关键文件:
   - `combined.py`: 包含原始代码 + 测试代码的可执行文件
   - `sample_code_inputs.txt`: 测试输入数据
   - `results.txt`: 预期的测试结果

**关键处理逻辑** (load_dataset.py:15-36):
```
process_test_field()
├── 定位 "inputs" 关键字
├── 删除 assertion 部分
└── 保留测试框架结构
```

**输出结构**:
```
output_mbppplus_new/
└── task_{task_id}/
    ├── task_{task_id}.json           # 原始任务数据
    ├── combined.py                   # 可执行代码
    ├── sample_code_inputs.txt       # 测试输入
    └── results.txt                   # 预期结果
```

---

### 阶段二：代码变异生成

**入口文件**: `equivalent_transform.py`

**功能**: 使用 LLM 生成语义等价的变异代码

**变异规则** (equivalent_transform.py:124-146):
1. **标识符与数据(ID)**: 函数/变量重命名、常量替换
2. **语法简化(TSS)**: 简写展开、操作数交换
3. **控制流(CF)**: for/while 循环互换、条件重构
4. **代码增强(CA)**: 插入死代码、格式化
5. **API重构(AFR)**: 等价API调用替换

**LLM 调用流程** (equivalent_transform.py:33-68):
```
call_llm()
├── 构建包含变异规则的系统提示
├── 调用 GPT-5.1 模型
├── 指数退避重试(最多5次)
└── 提取 <result>...</result> 块
```

**输出结构**:
```
equivalent_transform_new/
└── task_{task_id}.py    # LLM 生成的变异代码(语义等价)
```

---

### 阶段三：代码拼接与输入准备

**入口文件**: `splice_main_and_function.py`

**功能**: 将变异代码与测试框架拼接，生成可执行的测试文件

**拼接逻辑** (splice_main_and_function.py:32-72):
```
输入:
├── task_{id}.py (变异代码)
├── combined.py (原始代码+测试框架)
└── sample_code_inputs.txt (测试输入)

处理:
├── 读取变异代码
├── 读取测试输入
└── 拼接生成 sample_inputs_equivalent.py

输出:
sample_inputs_equivalent.py = 变异代码 + 测试输入 + 结果写入逻辑
```

**生成文件类型**:
- `sample_inputs_equivalent.py`: 语义等价的测试代码
- `sample_inputs_non_equivalent.py`: 语义不等价的测试代码
- `sample_original_correct.py`: 原始正确代码
- `sample_original_error.py`: 原始错误代码

---

### 阶段四：本地运行收集结果

**入口文件**: `run_code.py`

**功能**: 在本地执行测试代码，收集实际运行结果

**执行流程** (run_code.py:24-58):
```
for each task_folder:
    1. 定位 sample_inputs_{type}.py
    2. subprocess.run() 执行脚本
    3. 捕获 stdout/stderr
    4. 记录执行状态(成功/失败/超时)
```

**输出目录结构**:
```
# 根据执行结果分类存储
original_local/correct/      # 原始代码执行成功
original_local/error/        # 原始代码执行失败
equivalent_local/correct/    # 等价变异执行成功
equivalent_local/error/      # 等价变异执行失败
non_equivalent_local/correct/# 非等价变异执行成功
non_equivalent_local/error/  # 非等价变异执行失败
```

**输出文件格式** (task_{id}.txt):
```
'result': [val1, val2, val3]
'var1': [val1, val2]
...
```

---

### 阶段五：LLM 输出获取

**入口文件**: `run_tasks.py` + `utils.py`

**功能**: 将代码发送给 LLM，获取 LLM 输出的执行结果

**配置** (config1.json):
```json
{
  "api_key_fields": {
    "original": "...",
    "equivalent": "...",
    "non_equivalent": "..."
  },
  "output_paths": {
    "original": "sample_output_LLMs_original_code/minimax",
    "equivalent": "sample_output_LLMs_equivalent_code/minimax",
    "non_equivalent": "sample_output_LLMs_non_equivalent_code/minimax"
  }
}
```

**执行流程** (run_tasks.py:31):
```
execute_task_with_threads()
├── 并发处理多个任务
├── 对每个任务:
│   ├── 读取测试代码
│   ├── 构建 Prompt (要求 LLM 执行代码并输出结果)
│   ├── call_llm() 调用 LLM
│   └── 提取 <result>...</result> 块并保存
└── 保存结果到对应目录
```

**Prompt 构建** (utils.py:59-93):
```
You must execute the following Python code EXACTLY and return only the final results.

=== Python Code ===
{code_content}

Output format (strict):
<result>
line1
line2
...
</result>
```

---

### 阶段六：输出结果一致性评估

**入口文件**: `evaluate.py`

**功能**: 对比 LLM 输出与本地运行输出，找出第一个正确和第一个错误的测试用例

**评估流程** (evaluate.py:17-122):
```
对每个任务(task):
    1. 读取 LLM 输出 (sample_code_results.txt)
    2. 读取本地输出 (sample_code_compare_results.txt)
    3. 逐行对比过滤后的测试用例
    
    4. 找出第一个输出相同的输入 → 写入 *correct_inputs.txt
    5. 找出第一个输出不同的输入 → 写入 *error_inputs.txt
    
    6. 统计:
       - 完全正确: 所有测试用例输出相同
       - 部分正确: 部分测试用例输出相同
       - 完全错误: 所有测试用例输出不同
```

**关键过滤逻辑** (evaluate.py:75-79):
```python
# 过滤掉无效行(变异前后结果相同，认为该测试用例无效)
filtered_pairs = [
    (a, b)
    for a, b in zip(original_lines, sample_lines)
    if b != "变异前后结果相同，认为该测试用例无效"
]
```

**输出文件**:
```
output_mbppplus_new/task_{id}/
├── original_correct_inputs.txt   # 第一个输出相同的输入
├── original_error_inputs.txt    # 第一个输出不同的输入
├── equivalent_correct_inputs.txt
├── equivalent_error_inputs.txt
├── non_equivalent_correct_inputs.txt
└── non_equivalent_error_inputs.txt
```

---

### 阶段七：本地动态插桩获取变量序列

**入口文件**: `run_tracer.py` + `analysis_tracer.py`

**功能**: 通过 Python sys.settrace 追踪代码执行过程中的变量变化序列

**追踪原理** (analysis_tracer.py:14-46):
```
sys.settrace(tracer)
├── 监听 line/return 事件
├── 遍历当前帧的局部变量
├── 过滤系统变量(__*, inputs, inp, 函数, 模块)
├── 检测变量值变化
└── 记录变化序列
```

**变量变化检测** (analysis_tracer.py:32-44):
```python
prev_val = prev_locals.get(var, object())
if var not in prev_locals or prev_val != val:
    # 记录新值到序列
    var_sequences[var].append(safe_val)
    prev_locals[var] = copy.deepcopy(val)
```

**输出格式**:
```
'result': [val1, val2, val3]
'a': [1, 3, 7, 15]
'b': [2, 4, 8, 16]
'i': [0, 1, 2]
```

**批量执行** (run_tracer.py:20-52):
```
run_tracer.py
├── 扫描 target_dir 下的目标文件
├── 对每个文件调用 trace_variables()
└── 保存结果到 local_dirs/{type}/{task_id}.txt
```

---

### 阶段八：LLM 变量序列获取

**入口文件**: `run_llm_tracer.py`

**功能**: 将代码发送给 LLM，请求 LLM 模拟执行并返回变量变化序列

**Prompt 构建** (run_llm_tracer.py:63-94):
```
You must execute the following Python code EXACTLY and trace all variable changes.

=== Python Code ===
{code_content}

Output format (strict):
<result>
'var1': [val1, val2, val3]
'var2': [val1, val2]
...
</result>

Rules:
1. List every variable (except: inputs, inp, imported modules, functions, classes)
2. Each entry shows ALL values the variable took during execution, in order
```

**文件配置** (run_llm_tracer.py:15-22):
```python
FILE_CONFIG = {
    "sample_original_correct.py": ("original_llm", "correct", "original"),
    "sample_original_error.py":   ("original_llm", "error", "original"),
    "sample_equivalent_correct.py": ("equivalent_llm", "correct", "equivalent"),
    "sample_equivalent_error.py":  ("equivalent_llm", "error", "equivalent"),
    "sample_non_equivalent_correct.py": ("non_equivalent_llm", "correct", "non_equivalent"),
    "sample_non_equivalent_error.py":  ("non_equivalent_llm", "error", "non_equivalent"),
}
```

**并发处理** (run_llm_tracer.py:148-157):
- 6 路并发，每路处理一种文件类型
- 内部串行执行确保稳定性

---

### 阶段九：变量序列一致性评估

**入口文件**: `evaluate_trace.py`

**功能**: 对比 LLM 输出的变量序列与本地追踪的变量序列

**对比流程** (evaluate_trace.py:50-126):
```
compare_directories(llm_dir, local_dir)
├── 找到共同的文件 (task_*.txt)
├── 解析为字典格式 {'变量名': '变量值字符串'}
├── 对比维度:
│   ├── result 是否相同
│   └── 各变量序列是否相同
└── 统计:
    ├── result 相同的文件数
    ├── 所有变量都相同的文件数
    └── 变量维度匹配率
```

**评估指标**:
- **result 相同率**: 最终结果相同的任务比例
- **全变量相同率**: 所有变量变化序列都相同的任务比例
- **变量匹配率**: 相同变量数量 / 基准变量数量

**输出分类** (evaluate_trace.py:119-124):
- `all_match_files`: 所有变量都相同的文件
- `result_only_match_files`: result 相同但其他变量不同的文件

---

## 关键技术点

### 1. 线程安全的 LLM 客户端 (utils.py:9-14)
```python
thread_local = threading.local()

def get_client(api_key):
    if not hasattr(thread_local, "client"):
        thread_local.client = OpenAI(api_key=api_key)
    return thread_local.client
```

### 2. 指数退避重试机制 (utils.py:21-39)
```python
for attempt in range(max_retries):
    try:
        # 调用 LLM
    except Exception:
        time.sleep(2 ** attempt)  # 指数退避: 1, 2, 4, 8, 16
```

### 3. sys.settrace 变量追踪 (analysis_tracer.py:14-46)
```python
def tracer(frame, event, arg):
    if event in ("line", "return"):
        cur_locals = frame.f_locals.copy()
        for var, val in cur_locals.items():
            # 过滤并检测变化
            if var not in prev_locals or prev_val != val:
                var_sequences[var].append(val)
```

---

## 执行示例

### 完整执行流程:

```bash
# 1. 加载数据集
python load_dataset.py

# 2. 并发生成变异代码
python equivalent_transform.py

# 3. 拼接代码生成测试文件
python splice_main_and_function.py       # 等价
python splice_non_equivalent_function_and_main.py  # 非等价

# 4. 本地运行收集结果
python run_code.py

# 5. LLM 输出获取
python run_tasks.py --mode original --output_name minimax --model_name minimax
python run_tasks.py --mode equivalent --output_name minimax --model_name minimax
python run_tasks.py --mode non_equivalent --output_name minimax --model_name minimax

# 6. 评估输出结果一致性
python evaluate.py

# 7. 本地动态插桩获取变量序列
python run_tracer.py

# 8. LLM 变量序列获取
python run_llm_tracer.py --model_name minimax

# 9. 评估变量序列一致性
python evaluate_trace.py
```

---

## 目录结构总览

```
empirical/
├── load_dataset.py                    # 数据集加载
├── equivalent_transform.py            # 变异代码生成
├── splice_main_and_function.py        # 代码拼接(等价)
├── splice_non_equivalent_function_and_main.py  # 代码拼接(非等价)
├── run_code.py                        # 本地运行
├── run_tasks.py                       # LLM 输出获取
├── evaluate.py                        # 输出结果评估
├── run_tracer.py                      # 本地变量追踪
├── run_llm_tracer.py                  # LLM 变量序列获取
├── evaluate_trace.py                  # 变量序列评估
├── utils.py                           # 通用工具
├── analysis_tracer.py                  # 追踪器实现
│
├── output_mbppplus_new/               # 任务数据
│   └── task_{id}/
│
├── equivalent_transform_new/          # LLM 变异代码
├── sample_output_LLMs_*/              # LLM 输出结果
├── original_local/                    # 本地执行结果
├── equivalent_local/
├── non_equivalent_local/
├── original_llm/                     # LLM 变量序列
├── equivalent_llm/
└── non_equivalent_llm/
```

---

## 注意事项

1. **config1.json**: 需配置有效的 API_KEY 和各模式对应路径
2. **超时设置**: run_code.py 中 timeout=30 秒防止死循环
3. **并发控制**: 使用 ThreadPoolExecutor 控制并发数量
4. **变量过滤**: 追踪时自动过滤 inputs, inp, __* , 函数, 模块等
5. **输出路径**: 确保各目录有足够磁盘空间存储中间结果