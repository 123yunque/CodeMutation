from mutation_runner import (
    call_llm,
    extract_result_block,
    get_client,
    get_response_content,
    iter_folders,
    process_folder,
    read_code,
    run_mutation,
    validate_python_code,
)

import json
import os


def load_trace_cases(task_dir):
    if not task_dir:
        return []
    trace_path = os.path.join(task_dir, "original_statement_trace.jsonl")
    if not os.path.exists(trace_path):
        return []

    cases = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(
                {
                    "input_index": item.get("input_index"),
                    "input": item.get("input"),
                    "original_output": item.get("original_output_text"),
                    "statement_trace": item.get("statement_trace"),
                    "statement_trace_rle": item.get("statement_trace_rle"),
                }
            )
    return cases


def build_trace_context(task_dir):
    cases = load_trace_cases(task_dir)
    if not cases:
        return ""
    return f"""

Below are the sampled inputs, original outputs, and original executed statement traces for this task.
The statement trace uses AST statement positions such as body.0:Assign or body.1:If.body.0:Return.
For long repeated traces, statement_trace_rle is the run-length encoded form.
```json
{json.dumps(cases, ensure_ascii=False, indent=2)}
```
"""


def build_equivalent_prompt(code_content, **kwargs):
    return f"""
Below is the Python code:
{code_content}

You are a Mutation Testing Engineer. Generate a semantically equivalent version of the provided programming problem by applying a diverse set of transformations.

Mutation Rules:
1. Identifier & Data (ID): Rename functions/variables or replace literals with equivalent expressions.
2. Trivial Syntactic Shifts (TSS): Unfold shorthand, swap safe operands, or reorder independent statements.
3. Control Flow (CF): Interchange for/while loops or refactor conditionals without changing behavior.
4. Code Augmentation (CA): Insert unreachable/dead code or harmless formatting changes. Do not include comments or docstrings.
5. API & Function Refactoring (AFR): Use equivalent APIs or local function structures.

Requirements:
- Preserve 100% functional equivalence and I/O behavior.
- Apply at least 4 rules.
- Return only valid Python code.

Output ONLY the transformed code, wrapped exactly as:
<result>
<your_transformed_code_here>
</result>
"""


def build_non_equivalent_prompt(code_content, task_dir=None, **kwargs):
    trace_context = build_trace_context(task_dir)
    return f"""
Below is the Python code:
{code_content}
{trace_context}

You are a Mutation Testing Engineer. Introduce a single, subtle logical change that alters the correct answer of the problem while preserving the original executed statement trace.

Mutation Rules (pick exactly ONE):
1. Relational Operator Replacement (ROR): Flip a comparison, such as > to < or == to !=, only when it does not decide which control-flow body executes for the listed traces.
2. Logical Connector Replacement (LCR): Swap a logical connector, such as and to or.
3. Arithmetic Operator Replacement (AOR): Change an arithmetic operator, such as + to -, but do not replace list, tuple, or string concatenation with an unsupported operation.
4. Constant Value Mutation (CVM): Change a critical threshold or constant by a minimal margin.

Requirements:
- Change exactly one token, operator, or literal.
- Keep the rest of the code as close to the original as possible.
- For every listed input, the transformed code must execute the exact same statement_trace in the exact same order as the original code.
- For every listed input, the transformed code should produce an output different from the listed original_output. If that is impossible with one safe token change, still ensure at least one listed output changes.
- Keep function names, function signatures, imports, return locations, loop structures, and branch structures unchanged.
- Do not change called function names or method names. API replacement is not allowed for non-equivalent mutation.
- Do not add, delete, reorder, or reindent control-flow statements.
- Do not add comments, docstrings, print statements, helper functions, exception handling, randomness, file I/O, input calls, or new API calls.
- The transformed code must run successfully on every listed input.
- Preserve type compatibility and index safety for every listed input. Do not introduce out-of-range indexing, invalid container arithmetic, invalid method calls, or operations unsupported by the existing operand types.
- Avoid mutating expressions that control whether an if, while, or for body executes. Prefer mutating a returned value or assigned value that is already executed on the same trace.
- Avoid changing == or != in branch conditions when that would change which branch body executes.
- Avoid changing index expressions such as k - 1 to k unless every listed input is guaranteed to stay in range.
- Do not mutate code inside a branch body that is not executed by the listed statement_trace values.
- If an If statement appears in statement_trace but its body or orelse body does not appear, that missing branch body is unexecuted and must not be mutated.
- The changed token must be in an executed return expression, assignment expression, arithmetic expression, method argument, or constant that affects the listed outputs.
- Before returning the answer, mentally evaluate the listed original_output values. The transformed code must change at least one listed output; do not choose a mutation that leaves all listed outputs unchanged.
- Ensure the original correct solution becomes incorrect for at least one listed input.
- Prefer changing outputs for as many listed inputs as possible.
- Return only valid Python code.

Forbidden changes:
- Do not change a list, tuple, or string + concatenation into -, *, /, %, or another unsupported operator.
- Do not mutate an index expression when any listed input can hit the first or last element.
- Do not mutate subscript/index expressions at all, including arr[k - 1], arr[k], seq[i], text[0], or num[j].
- Never change one-based indexing corrections such as arr[k - 1], arr[k-1], seq[n - 1], or seq[n-1] into arr[k] or seq[n].
- Treat branch and loop conditions as read-only unless you can prove every listed statement_trace remains identical. Do not mutate them if any listed trace would take a different body, skip a body, or add a body execution.
- Do not return a mutation that only changes behavior for rare boundary inputs when a return-value or assigned-value mutation can change more listed outputs.
- Do not return code with added, removed, or rewritten comments/docstrings.
- Do not replace method names such as capitalize, title, union, intersection, replace, split, join, append, or sort.

Internal self-check before final output:
1. All listed inputs run without exceptions.
2. All listed statement_trace sequences remain exactly identical.
3. As many listed outputs as possible, preferably every listed output, differ from original_output.

Output ONLY the transformed code, wrapped exactly as:
<result>
<your_transformed_code_here>
</result>
"""


def prompt_builder_for_mode(mode):
    if mode == "equivalent":
        return build_equivalent_prompt
    if mode == "non_equivalent":
        return build_non_equivalent_prompt
    raise ValueError(f"Unknown mutation mode: {mode}")
