# Project Pipeline Overview

A systematic pipeline for empirical study of code transformations and variable change tracking.

## 1. Project Introduction

This project investigates how large language models (LLMs) handle code transformations through mutation testing. It creates variants of programming tasks and analyzes the impact on variable execution traces.

### Core Research Questions
- How do equivalent transformations affect runtime behavior?
- Can variable change sequences serve as fingerprints for code equivalence?
- What mutation rules preserve vs. alter program semantics?

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATASET LAYER                                   │
│                    (MBPP++ from HuggingFace)                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PREPROCESSING LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                    │
│  │ sample_load │  │ load_dataset │  │sample_code  │                    │
│  └──────────────┘  └──────────────┘  └──────────────┘                    │
│         │                 │                  │                            │
│         ▼                 ▼                  ▼                            │
│  ┌──────────────────────────────────────────────────┐                   │
│  │            output_mbppplus_new/                   │                   │
│  │   task_XXX/{code.py, combined.py, inputs.txt}     │                   │
│  └──────────────────────────────────────────────────┘                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION LAYER                                │
│                                                                     │
│  ┌─────────────────────┐    ┌─────────────────────┐                   │
│  │ equivalent_transform│    │noequivalent_transform│                │
│  │      (preserve)      │    │      (alter)        │                  │
│  └─────────────────────┘    └─────────────────────┘                   │
│             │                           │                             │
│             ▼                           ▼                             │
│  equivalent_transform_new/    non_equivalent_transform_new/        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ANALYSIS & TRACING LAYER                             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ analysis.py  │  │batch_run_    │  │analysis_    │                 │
│  │(dynapyt)     │  │analysis.py   │  │tracer.py    │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
│         │                 │                  │                            │
│         ▼                 ▼                  ▼                            │
│  ┌──────────────────────────────────────────────────┐                │
│  │       Variable Change Sequences                   │                │
│  │  original_local/*.txt + collected_sequences/    │                │
│  └──────────────────────────────────────────────────┘                │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       EVALUATION LAYER                                   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ evaluate.py │  │evaluate_    │  │evaluate_     │                 │
│  │             │  │trace.py     │  │equivalent.py │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Complete Pipeline Workflow

### Step 1: Dataset Loading
```
Files: sample_load.py, load_dataset.py, sample_code.py

Process:
1. Load MBPP++ dataset from HuggingFace (evalplus/mbppplus)
2. Parse task metadata (task_id, code, test, prompt)
3. Generate task directories under output_mbppplus_new/
4. Extract inputs and results from test field
5. Create combined.py files for execution
```

### Step 2: Code Transformations
```
Equivalent Transform:
  File: equivalent_transform.py
  Rules: ID, TSS, CF, CA, AFR
  Output: equivalent_transform_new/
  Constraint: 100% functional equivalence

Non-Equivalent Transform:
  File: noequivalent_transform.py
  Rules: ROR, LCR, AOR, CVM
  Output: non_equivalent_transform_new/
  Constraint: Semantic shift required
```

### Step 3: Variable Tracking
```
Analysis Tool: dynapyt (dynamic analysis framework)
Files: analysis.py, batch_run_analysis.py, analysis_tracer.py

Process:
1. Instrument Python code with trace hooks
2. Execute code and capture variable writes
3. Record variable name + value at each write point
4. Generate variable change sequence: 'variable': [val1, val2, ...]
5. Output to .txt files
```

### Step 4: Evaluation & Comparison
```
Files: evaluate.py, evaluate_trace.py, evaluate_equivalent.py

Metrics:
- Output consistency (line-by-line comparison)
- Variable sequence equivalence
- Functional equivalence validation

Directories:
- output_mbppplus_new/ (baseline)
- equivalent_transform_new/ (transformed)
- non_equivalent_transform_new/ (mutated)
```

---

## 4. Mutation Rules Reference

### Equivalent Transformation Rules

| Rule | Abbreviation | Description | Example |
|------|-------------|-------------|---------|
| Identifier & Data | ID | Rename functions/variables | `def solve()` → `def fun1()` |
| Trivial Syntactic Shift | TSS | Unfold shorthand, swap operands | `x++` → `x=x+1` |
| Control Flow | CF | Loop interchange, ternary | `for` ↔ `while` |
| Code Augmentation | CA | Insert dead code | `if False: pass` |
| API Refactoring | AFR | Equivalent API calls | Alternative implementation |

### Non-Equivalent Transformation Rules

| Rule | Abbreviation | Description | Example |
|------|-------------|-------------|---------|
| Relational Operator Replace | ROR | Flip comparison | `>` → `<` |
| Logical Connector Replace | LCR | Swap AND/OR | `and` → `or` |
| Arithmetic Operator Replace | AOR | Change operator | `+` → `-` |
| Constant Value Mutation | CVM | Alter threshold | `limit=10` → `11` |

---

## 5. Usage

### Quick Start

```bash
# 1. Load dataset
python sample_load.py

# 2. Generate equivalent transforms
python equivalent_transform.py

# 3. Generate non-equivalent transforms
python noequivalent_transform.py

# 4. Run variable tracking
python batch_run_analysis.py

# 5. Evaluate results
python evaluate.py
```

### Configuration

Edit `config.json` to set API keys:

```json
{
  "API_KEY": "your-key-here",
  "original": "sk-...",
  "non_equivalent": "sk-...",
  "equivalent": "sk-..."
}
```

---

## 6. Directory Structure

```
empirical/
├── output_mbppplus_new/           # Original tasks (task_XXX/)
│   └── task_XXX/
│       ├── code.py
│       ├── combined.py
│       ├── code_inputs.txt
│       └── task_XXX.json
├── equivalent_transform_new/     # Equiv. transforms (.py files)
├── non_equivalent_transform_new/ # Non-equiv. transforms (.py files)
├── original_local/               # Variable sequences (baseline)
├── collected_sequences/        # Variable sequences (transformed)
└── PROJECT_PIPELINE.md         # This document
```

---

## 7. Key Outputs

- **Variable Change Sequences**: Text files capturing variable states during execution
- **Transformed Code**: Semantically equivalent and mutated variants
- **Evaluation Reports**: Metrics on transformation effectiveness

---

## 8. Dependencies

- Python 3.8+
- dynapyt (dynamic analysis)
- openai (API calls)
- datasets (HuggingFace)
- httpx (HTTP client)

Install via:
```bash
pip install -r requirements.txt
```