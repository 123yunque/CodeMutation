# Project Overview

This project is designed to apply programmatic code transformations and analyze their impact through systematic evaluation and testing. It involves generating input data, processing results, and intelligently transforming programs using LLMs (Large Language Models). The pipeline ensures an extensible workflow for machine-coded testing and evaluation.

## Table of Contents

- [Modules Overview](#modules-overview)
- [Workflow](#workflow)
  - [Dataset Processing](#dataset-processing)
  - [Code Transformations](#code-transformations)
  - [Evaluation](#evaluation)
  - [Task Execution](#task-execution)
- [Dependency Setup](#dependency-setup)

## Modules Overview

### **1. `analysis.py`**
Analyzes and tracks variable changes during code execution. Logs results to enable comparisons.
- Defines `BatchVariableTracker`, an analysis class to create variable sequences based on code instrumentation.
- Loads instrumentation mappings with support for cached JSON.
- Writes collected variable sequences (`var_sequences`) into output files for further evaluation.

---
### **2. `batch_run_analysis.py`**
Executes batch analysis on multiple input programs.
- Identifies, processes, and instruments multiple Python files.
- Outputs unified logs and tracking files for batch processing.

---
### **3. `analysis_tracer.py`**
Traces runtime variable changes in Python scripts.
- Defines `trace_variables(filepath)` to inspect runtime variable flow per step.
- Used to capture runtime traces for program execution analysis.

---
### **4. `evaluate.py`**
Compares outputs from different code models or code versions.
- Reads result files and compares line-by-line equivalence.
- Produces detailed metrics for results overlap, file correctness, and similarity analysis of predictions.

---
### **5. `evaluate_trace.py`**
Compares LLM results against a baseline dataset.
- Cross-verifies specified directory structures (e.g., `equivalent_llm`).
- Evaluates variable equivalence and correctness consistency across files.

---
### **6. `evaluate_equivalent.py`**
Analyzes functional equivalence in input-output mappings.
- Passes transformations to compare the effect of logically equivalent model-states or functions.

---
### **7. `run_code.py`**
Automates running generated Python programs across multiple tasks.
- Executes each task's Python script and captures its runtime output.
- Provides post-run summaries of success/failure rates for execution.

---
### **8. `noequivalent_transform.py`**
Generates logically **non-equivalent** mutations of programs.
- Uses LLMs for targeted code transformation using defined mutation rules (like replacing relational operators).
- Writes transformed code back to a new directory (`non_equivalent_transform_new`).

---
### **9. `equivalent_transform.py`**
Applies functionally equivalent but syntactically altered transformations to code.
- Supports multi-rule transformations: renames, loop-unroll, augmentations, etc.
- Ensures that the valid syntactic shift maintains complete functional equivalence.

---
### **10. `run_tasks.py`**
Implements dynamic execution of tasks in multiple pre-configured modes (original, non-equivalent, equivalent).
- Parses the `config.json` input and dynamically adjusts task dispatch for all modes.

---
### **11. `sample_code.py`**
Performs file manipulations for synthetic input generation:
- Appends task-level metadata and configuration into `sample_code_inputs.txt` dynamically.
- Manages combined and runtime file preparation at runtime.

---
### **12. `sample_load.py`**
Processes the evaluation dataset for generating task directories.
- Loads dataset and parses configurations across all tasks (e.g., `task_{ID}`).
- Handles extraction of task properties like `inputs`, `outputs`, and code snippets.

---
### **13. `utils.py`**
Utility toolset abstracting threaded processing, I/O operations, and robust OpenAI interactions.
- Threads API clients to maximize parallel execution for large batches.
- Implements retry/backoff patterns for handling varied API limits.


## Workflow

This project involves multiple layers of operation including dataset loading, program mutation, evaluation, and task management.

### **1. Dataset Processing**
Relevant Files:
- `sample_load.py`

The `MBPP++ Dataset` is parsed into distinct task folders (`task_{ID}`), containing task metadata, code, test inputs, and outputs. Example task files:

```text
- task_001/
  - code.py
  - combined.py
  - inputs.txt
  - results.json
```

### **2. Code Transformations**
#### **Equivalent Transformations**
Relevant Files:
- `equivalent_transform.py`

This step creates equivalent programs by applying transformations: loop unrolling, renaming, or leveraging semantic-preservation rules.

#### **Non-Equivalent Transformations**
Relevant Files:
- `noequivalent_transform.py`

Mutates input programs such that correctness is intentionally altered (e.g., flipping a relational operator). Outputs are saved in structured experiment folders.

### **3. Evaluation**
#### Compare Output Consistency
Relevant Files:
- `evaluate_everything.py` / `evaluate_trace.py`

Systematically compares outputs generated by transformed programs against baseline results. Logs details about mismatches and validation scores.

### **4. Task Execution**
Tasks can be executed in one of three modes:

- **`original`**: Executes unmodified programs as-is.
- **`non_equivalent`**: Runs intentionally mutated programs.
- **`equivalent`**: Executes equivalent-transformed programs for observable differences.

Files or Utilities:
- `run_tasks.py`
- `analysis.py` & evaluation suites


## Dependency Setup

**Requirements:**
- Python 3.8+
- Additional libraries: OpenAI SDK, Datasets library, ThreadExecutor

```bash
pip install -r requirements.txt
```

Ensure `config.json` is configured with API keys and paths.