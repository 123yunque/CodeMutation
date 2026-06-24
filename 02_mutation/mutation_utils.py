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


def build_equivalent_prompt(code_content):
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


def build_non_equivalent_prompt(code_content):
    return f"""
Below is the Python code:
{code_content}

You are a Mutation Testing Engineer. Introduce a single, subtle logical change that alters the correct answer of the problem while preserving the original execution-line trace.

Mutation Rules (pick exactly ONE):
1. Relational Operator Replacement (ROR): Flip a comparison, such as > to < or == to !=.
2. Logical Connector Replacement (LCR): Swap a logical connector, such as and to or.
3. Arithmetic Operator Replacement (AOR): Change an arithmetic operator, such as + to -.
4. Constant Value Mutation (CVM): Change a critical threshold or constant by a minimal margin.

Requirements:
- Change exactly one token, operator, or literal.
- Keep the rest of the code as close to the original as possible.
- Preserve the same number of lines as the original code.
- Do not add, delete, reorder, or reindent any line.
- Do not change function names, function signatures, imports, return locations, loop structures, or branch structures.
- Do not add comments, docstrings, print statements, helper functions, exception handling, or new API calls.
- The generated code must execute the same source line sequence as the original code for the same inputs.
- Ensure the original correct solution becomes incorrect for at least one input.
- Return only valid Python code.

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
