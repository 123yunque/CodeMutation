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


def format_sample_examples(sample_context, include_outputs=False):
    examples = (sample_context or {}).get("examples", [])[:5]
    if not examples:
        return "- (no sampled inputs available)"
    lines = []
    for example in examples:
        if include_outputs and example.get("output") is not None:
            lines.append(f"- input: {example.get('input')}\n  original_output: {example.get('output')}")
        else:
            lines.append(f"- input: {example.get('input')}")
    return "\n".join(lines)


def build_equivalent_prompt(code_content, sample_context=None):
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


def build_non_equivalent_prompt(code_content, sample_context=None):
    return f"""
Below is the Python code:
{code_content}

Sampled inputs from this task:
{format_sample_examples(sample_context, include_outputs=True)}

You are a Mutation Testing Engineer. Introduce a single, subtle logical change that alters the correct answer of the problem.

Mutation Rules (pick exactly ONE):
1. Relational Operator Replacement (ROR): Flip a comparison, such as > to < or == to !=.
2. Logical Connector Replacement (LCR): Swap a logical connector, such as and to or.
3. Arithmetic Operator Replacement (AOR): Change an arithmetic operator, such as + to -.
4. Constant Value Mutation (CVM): Change a critical threshold or constant by a minimal margin.

Requirements:
- Change exactly one token, operator, or literal.
- Keep the rest of the code as close to the original as possible.
- Preserve the original function name, function signature, imports, return type shape, and input/output format.
- The mutated code MUST run without exceptions for every sampled input listed above.
- Ensure at least one sampled input listed above produces a different output from the original.
- Do not mutate loop bounds, slice bounds, or indexing in a way that can create empty max/min calls or out-of-range access.
- Prefer changing a comparison threshold, relational operator, boolean connector, arithmetic operator, or a numeric/string literal that directly affects the returned value.
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
