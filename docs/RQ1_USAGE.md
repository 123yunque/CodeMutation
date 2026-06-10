# RQ1 Usage Guide

This guide describes the current RQ1 workflow after refactoring. Removed legacy entry files such as `sample_load.py`, `run_code.py`, `run_tasks.py`, and `evaluate.py` are no longer used.

## Current Structure

```text
rq1_config.py                 # Shared RQ1 mode/file/path config

01_data/
  data_main.py                # Dataset preparation CLI
  data_utils.py               # Dataset loading, input parsing, task writing

02_mutation/
  mutation_main.py            # Mutation generation CLI
  mutation_utils.py           # Equivalent/non-equivalent prompts
  mutation_runner.py          # LLM mutation generation and syntax validation

03_splice/
  splice_main.py              # Executable sample script generation CLI
  splice_utils.py             # Function detection, input loading, script building

04_local_exec/
  exec_main.py                # Local execution CLI
  exec_utils.py               # Subprocess execution and non-equivalent result comparison

05_rq1/
  validate_main.py            # Validate mutation quality using 04 local outputs
  validate_utils.py           # Validation report and optional mutation retry
  rq1_main.py                 # RQ1 LLM run/evaluate CLI
  rq1_utils.py                # RQ1 LLM execution and evaluation logic
```

## Workflow

```text
01_data -> 02_mutation -> 03_splice -> 04_local_exec -> 05_rq1/validate -> 05_rq1/rq1
```

Responsibilities:

```text
01_data       Prepare MBPP++ task folders
02_mutation   Generate equivalent and non-equivalent mutation code
03_splice     Build executable sample scripts
04_local_exec Execute sample scripts and write local result files
05_validate   Check whether mutations are valid using local result files
05_rq1        Run/evaluate LLM execution results for RQ1
```

## 1. Prepare Data

Generate or refresh `output_mbppplus_new/task_x`:

```powershell
python 01_data\data_main.py --sample_size 10 --seed 0 --overwrite
```

Quick test:

```powershell
python 01_data\data_main.py --limit 5 --sample_size 10 --seed 0 --overwrite
```

If `output_mbppplus_new` already exists and is correct, you usually do not need to rerun this step.

## 2. Generate Mutations

Equivalent mutations:

```powershell
python 02_mutation\mutation_main.py --mode equivalent --max_workers 2
```

Non-equivalent mutations:

```powershell
python 02_mutation\mutation_main.py --mode non_equivalent --max_workers 2
```

Quick test:

```powershell
python 02_mutation\mutation_main.py --mode equivalent --limit 5 --max_workers 1
python 02_mutation\mutation_main.py --mode non_equivalent --limit 5 --max_workers 1
```

Overwrite existing mutation files:

```powershell
python 02_mutation\mutation_main.py --mode equivalent --overwrite
python 02_mutation\mutation_main.py --mode non_equivalent --overwrite
```

Outputs:

```text
equivalent_transform_new/task_x.py
non_equivalent_transform_new/task_x.py
```

## 3. Build Executable Samples

Build all sample scripts:

```powershell
python 03_splice\splice_main.py --mode all
```

Build one mode only:

```powershell
python 03_splice\splice_main.py --mode original
python 03_splice\splice_main.py --mode equivalent
python 03_splice\splice_main.py --mode non_equivalent
```

Outputs in each task folder:

```text
sample_inputs.py
sample_original.py
sample_inputs_equivalent.py
sample_inputs_non_equivalent.py
```

## 4. Run Local Execution

Run all modes and generate non-equivalent compare files:

```powershell
python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent
```

Run one mode:

```powershell
python 04_local_exec\exec_main.py --mode original --timeout 30
python 04_local_exec\exec_main.py --mode equivalent --timeout 30
python 04_local_exec\exec_main.py --mode non_equivalent --timeout 30
```

Quick test:

```powershell
python 04_local_exec\exec_main.py --mode equivalent --limit 5 --timeout 30
```

Outputs in each task folder:

```text
sample_code_results.txt
sample_code_results_equivalent.txt
sample_code_results_non_equivalent.txt
sample_code_compare_results.txt
```

`exec_main.py` fixes `PYTHONHASHSEED=0` during local execution to avoid false mismatches caused by set/tuple order.

## 5. Validate Mutation Quality

`05_rq1/validate_main.py` checks the local result files produced by `04_local_exec`.

Default behavior: validate existing local results only. It does not rerun local execution and does not call LLM retry.

```powershell
python 05_rq1\validate_main.py
```

Quick validation:

```powershell
python 05_rq1\validate_main.py --limit 5
```

Rerun local execution before validation:

```powershell
python 05_rq1\validate_main.py --run_exec
```

Retry failed mutations with LLM feedback:

```powershell
python 05_rq1\validate_main.py --retry
```

Rerun local execution and retry:

```powershell
python 05_rq1\validate_main.py --run_exec --retry
```

Reports:

```text
reports/mutation_failures.json
reports/mutation_failures_after_retry.json
```

Validation meaning:

```text
original vs equivalent:
  same    -> equivalent mutation passes
  differ  -> equivalent mutation fails

original vs non_equivalent:
  differ  -> non-equivalent mutation passes
  same    -> non-equivalent mutation fails
```

## 6. Run RQ1 LLM Tasks

Run original:

```powershell
python 05_rq1\rq1_main.py run --mode original --output_name gpt51 --model_name gpt-5.1 --max_workers 2
```

Small smoke run:

```powershell
python 05_rq1\rq1_main.py run --mode original --output_name gpt51_smoke --model_name gpt-5.1 --max_workers 1 --limit 3 --overwrite
```

Run equivalent:

```powershell
python 05_rq1\rq1_main.py run --mode equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
```

Run non-equivalent:

```powershell
python 05_rq1\rq1_main.py run --mode non_equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
```

Overwrite existing LLM outputs:

```powershell
python 05_rq1\rq1_main.py run --mode equivalent --output_name gpt51 --model_name gpt-5.1 --overwrite
```

LLM output directories:

```text
sample_output_LLMs_original_code/<output_name>/task_x.txt
sample_output_LLMs_equivalent_code/<output_name>/task_x.txt
sample_output_LLMs_non_equivalent_code/<output_name>/task_x.txt
```

## 7. Evaluate RQ1

Evaluate all modes:

```powershell
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51
```

Write JSON report:

```powershell
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51 --report reports\rq1_gpt51.json
```

Do not refresh correct/error input files:

```powershell
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51 --no_write_inputs
```

## Recommended Commands

If mutation files already exist, refresh executable samples, execute locally, then validate:

```powershell
python 03_splice\splice_main.py --mode all
python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent
python 05_rq1\validate_main.py
```

Full RQ1 preparation:

```powershell
python 02_mutation\mutation_main.py --mode equivalent --max_workers 2
python 02_mutation\mutation_main.py --mode non_equivalent --max_workers 2
python 03_splice\splice_main.py --mode all
python 04_local_exec\exec_main.py --mode all --timeout 30 --compare_non_equivalent
python 05_rq1\validate_main.py
```

Full RQ1 LLM run and evaluation:

```powershell
python 05_rq1\rq1_main.py run --mode original --output_name gpt51 --model_name gpt-5.1 --max_workers 2
python 05_rq1\rq1_main.py run --mode equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
python 05_rq1\rq1_main.py run --mode non_equivalent --output_name gpt51 --model_name gpt-5.1 --max_workers 2
python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51 --report reports\rq1_gpt51.json
```

## Config

`config1.json` must provide API settings and input paths:

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

Environment variable form is supported:

```json
"original": "${YUNWU_API_KEY}"
```
