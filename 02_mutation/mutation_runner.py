# [auto-patched by patch_imports.py]
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).parent.parent))

from config_loader import load_config
from paths import EQUIV_TRANSFORM, MBPP_DIR, NON_EQUIV_TRANSFORM

import ast
import copy
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


MODE_OUTPUTS = {
    "equivalent": EQUIV_TRANSFORM,
    "non_equivalent": NON_EQUIV_TRANSFORM,
}

thread_local = threading.local()


def task_sort_key(name):
    match = re.search(r"(\d+)$", name)
    return int(match.group(1)) if match else name


class LegacyOpenAIClient:
    def __init__(self, openai_module, api_key, base_url):
        self.openai = openai_module
        self.openai.api_key = api_key
        self.openai.api_base = base_url

    def create_chat_completion(self, model_name, messages, timeout):
        return self.openai.ChatCompletion.create(
            model=model_name,
            messages=messages,
            request_timeout=timeout,
        )


class ModernOpenAIClient:
    def __init__(self, client):
        self.client = client

    def create_chat_completion(self, model_name, messages, timeout):
        return self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            timeout=timeout,
        )


def get_client(api_key, base_url):
    if not hasattr(thread_local, "client"):
        import openai

        if hasattr(openai, "OpenAI"):
            thread_local.client = ModernOpenAIClient(openai.OpenAI(api_key=api_key, base_url=base_url))
        elif hasattr(openai, "ChatCompletion"):
            thread_local.client = LegacyOpenAIClient(openai, api_key, base_url)
        else:
            raise RuntimeError("Unsupported openai SDK: missing OpenAI and ChatCompletion clients")
    return thread_local.client


def get_response_content(response):
    if hasattr(response, "choices"):
        return response.choices[0].message.content
    return response["choices"][0]["message"]["content"]


def call_llm(prompt, folder, api_key, base_url, model_name, max_retries=5):
    messages = [
        {"role": "system", "content": "Return ONLY the modified code, no explanation, no reasoning."},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(max_retries):
        try:
            client = get_client(api_key, base_url)
            response = client.create_chat_completion(model_name, messages, timeout=240)
            content = get_response_content(response)
            if content and content.strip():
                return content
            print(f"[empty] {folder} attempt={attempt + 1}")
        except Exception as exc:
            print(f"[error] {folder} attempt={attempt + 1}: {exc}")
        time.sleep(2 ** attempt)

    return None


def extract_result_block(text):
    if not text:
        return "ERROR: LLM returned no result"
    match = re.search(r"<result>(.*?)</result>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def validate_python_code(code_text):
    try:
        ast.parse(code_text)
    except SyntaxError as exc:
        return False, f"{exc.msg} at line {exc.lineno}"
    return True, ""


def get_first_function_name(code_text):
    tree = ast.parse(code_text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


def read_code(task_dir):
    code_path = os.path.join(task_dir, "code.py")
    if not os.path.exists(code_path):
        return None
    with open(code_path, "r", encoding="utf-8") as f:
        return f.read()


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def read_sample_context(task_dir):
    input_lines = read_lines(os.path.join(task_dir, "sample_code_inputs.txt"))
    result_lines = read_lines(os.path.join(task_dir, "sample_code_results.txt"))
    examples = []
    for index, input_line in enumerate(input_lines):
        examples.append(
            {
                "input": input_line,
                "output": result_lines[index] if index < len(result_lines) else None,
            }
        )
    return {"examples": examples}


def validate_sample_behavior(code_text, sample_context, mode):
    examples = sample_context.get("examples", [])
    if not examples or any(example.get("output") is None for example in examples):
        return True, ""

    try:
        func_name = get_first_function_name(code_text)
        if not func_name:
            return False, "missing function definition"

        namespace = {}
        exec(code_text, namespace)
        func = namespace.get(func_name)
        if not callable(func):
            return False, f"missing callable: {func_name}"

        outputs = []
        for example in examples:
            args = ast.literal_eval(example["input"])
            result = func(*copy.deepcopy(args))
            outputs.append(str(result))
    except Exception as exc:
        return False, f"sample execution failed: {type(exc).__name__}: {exc}"

    expected = [example.get("output") for example in examples]
    if mode == "equivalent" and outputs != expected:
        return False, "equivalent outputs differ on sampled inputs"
    if mode == "non_equivalent" and outputs == expected:
        return False, "non-equivalent outputs did not differ on sampled inputs"
    return True, ""


def replacement_nodes(node):
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        op_type = type(node.ops[0])
        choices = [ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq]
        return [choice() for choice in choices if choice is not op_type]
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return [ast.Or()]
        if isinstance(node.op, ast.Or):
            return [ast.And()]
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        choices = [ast.Add, ast.Sub, ast.Mult]
        return [choice() for choice in choices if choice is not op_type]
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool):
            return [ast.Constant(not value)]
        if isinstance(value, int):
            return [ast.Constant(value + 1), ast.Constant(value - 1)]
        if isinstance(value, float):
            return [ast.Constant(value + 1.0), ast.Constant(value - 1.0)]
        if isinstance(value, str) and value:
            return [ast.Constant(value[:-1])]
    return []


class SingleMutationTransformer(ast.NodeTransformer):
    def __init__(self, target_index, replacement_index):
        self.target_index = target_index
        self.replacement_index = replacement_index
        self.current_index = -1

    def generic_visit(self, node):
        options = replacement_nodes(node)
        if options:
            self.current_index += 1
            if self.current_index == self.target_index:
                if isinstance(node, ast.Compare):
                    node = copy.deepcopy(node)
                    node.ops[0] = options[self.replacement_index]
                    return node
                if isinstance(node, ast.BoolOp):
                    node = copy.deepcopy(node)
                    node.op = options[self.replacement_index]
                    return node
                if isinstance(node, ast.BinOp):
                    node = copy.deepcopy(node)
                    node.op = options[self.replacement_index]
                    return node
                return options[self.replacement_index]
        return super().generic_visit(node)


class MutationOptionCollector(ast.NodeVisitor):
    def __init__(self):
        self.option_counts = []

    def generic_visit(self, node):
        options = replacement_nodes(node)
        if options:
            self.option_counts.append(len(options))
        super().generic_visit(node)


def deterministic_non_equivalent_candidate(code_content, sample_context, max_candidates=200):
    try:
        tree = ast.parse(code_content)
    except SyntaxError:
        return None, "original code does not parse"

    mutation_count = 0
    collector = MutationOptionCollector()
    collector.visit(tree)
    option_counts = collector.option_counts

    checked = 0
    last_error = "no mutation points found"
    for target_index, option_count in enumerate(option_counts):
        for replacement_index in range(option_count):
            if checked >= max_candidates:
                return None, last_error
            checked += 1
            candidate_tree = copy.deepcopy(tree)
            transformer = SingleMutationTransformer(target_index, replacement_index)
            candidate_tree = transformer.visit(candidate_tree)
            ast.fix_missing_locations(candidate_tree)
            candidate_code = ast.unparse(candidate_tree)
            ok, error = validate_sample_behavior(candidate_code, sample_context, "non_equivalent")
            if ok:
                return candidate_code, ""
            last_error = error
            mutation_count += 1

    return None, last_error if mutation_count else "no mutation points found"


def build_prompt(prompt_builder, code_content, sample_context):
    try:
        return prompt_builder(code_content, sample_context)
    except TypeError:
        return prompt_builder(code_content)


def process_folder(
    folder,
    input_dir,
    output_dir,
    prompt_builder,
    api_key,
    base_url,
    model_name,
    overwrite=False,
    validate=True,
):
    save_file = os.path.join(output_dir, f"{folder}.py")
    if os.path.exists(save_file) and not overwrite:
        return f"[skip] output exists: {folder}"
    if os.path.exists(save_file) and overwrite:
        os.remove(save_file)

    task_dir = os.path.join(input_dir, folder)
    if not os.path.isdir(task_dir):
        return f"[skip] not a task directory: {folder}"

    code_content = read_code(task_dir)
    if code_content is None:
        return f"[missing] {folder}/code.py"

    sample_context = read_sample_context(task_dir)
    mode = "non_equivalent" if "non_equiv" in str(output_dir) else "equivalent"
    last_error = ""
    for candidate_attempt in range(3):
        llm_output = call_llm(
            build_prompt(prompt_builder, code_content, sample_context),
            folder,
            api_key,
            base_url,
            model_name,
        )
        final_result = extract_result_block(llm_output)

        if validate:
            is_valid, error = validate_python_code(final_result)
            if not is_valid:
                last_error = error
                print(f"[invalid] {folder} candidate={candidate_attempt + 1}: {error}")
                continue

            behavior_ok, behavior_error = validate_sample_behavior(final_result, sample_context, mode)
            if not behavior_ok:
                last_error = behavior_error
                print(f"[invalid] {folder} candidate={candidate_attempt + 1}: {behavior_error}")
                continue

        with open(save_file, "w", encoding="utf-8") as f:
            f.write(final_result)
        return f"[done] {folder}"

    if mode == "non_equivalent":
        fallback_code, fallback_error = deterministic_non_equivalent_candidate(code_content, sample_context)
        if fallback_code:
            with open(save_file, "w", encoding="utf-8") as f:
                f.write(fallback_code)
            return f"[done] {folder} deterministic_fallback"
        last_error = fallback_error

    return f"[invalid] {folder}: {last_error}"


def iter_folders(input_dir, limit=None):
    folders = sorted(
        (f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))),
        key=task_sort_key,
    )
    if limit is not None:
        return folders[:limit]
    return folders


def run_mutation(
    mode,
    prompt_builder,
    output_dir=None,
    input_dir=None,
    model_name=None,
    api_key=None,
    base_url=None,
    max_workers=2,
    overwrite=False,
    limit=None,
    validate=True,
):
    config = load_config()
    input_dir = input_dir or str(MBPP_DIR)
    output_dir = output_dir or str(MODE_OUTPUTS[mode])
    model_name = model_name or config.get("model_name", "gpt-5.1")
    api_key = api_key or config["api_key_fields"][mode]
    base_url = base_url or config.get("yunwu_base_url") or config.get("api_base_url")

    if not api_key:
        raise ValueError(f"Missing API key for mode: {mode}")
    if not base_url:
        raise ValueError("Missing base URL. Set yunwu_base_url or api_base_url in config1.json.")

    os.makedirs(output_dir, exist_ok=True)
    folders = iter_folders(input_dir, limit)
    print(f"Running mutation mode={mode}, tasks={len(folders)}, model={model_name}, max_workers={max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_folder,
                folder,
                input_dir,
                output_dir,
                prompt_builder,
                api_key,
                base_url,
                model_name,
                overwrite,
                validate,
            )
            for folder in folders
        ]
        for future in as_completed(futures):
            try:
                print(future.result())
            except Exception as exc:
                print(f"[error] worker failed: {exc}")
