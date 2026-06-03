from pathlib import Path
import os

from paths import LLM_EQUIV, LLM_NON_EQUIV, LLM_ORIGINAL, MBPP_DIR


TASK_ROOT = Path(MBPP_DIR)

MODE_CONFIG = {
    "original": {
        "input_script": "sample_inputs.py",
        "local_result": "sample_code_results.txt",
        "llm_root": LLM_ORIGINAL,
        "correct_input": "original_correct_inputs.txt",
        "error_input": "original_error_inputs.txt",
    },
    "equivalent": {
        "input_script": "sample_inputs_equivalent.py",
        "local_result": "sample_code_results_equivalent.txt",
        "llm_root": LLM_EQUIV,
        "correct_input": "equivalent_correct_inputs.txt",
        "error_input": "equivalent_error_inputs.txt",
    },
    "non_equivalent": {
        "input_script": "sample_inputs_non_equivalent.py",
        "local_result": "sample_code_compare_results.txt",
        "llm_root": LLM_NON_EQUIV,
        "correct_input": "non_equivalent_correct_inputs.txt",
        "error_input": "non_equivalent_error_inputs.txt",
    },
}


def valid_modes():
    return tuple(MODE_CONFIG.keys())


def get_mode_config(mode):
    try:
        return MODE_CONFIG[mode]
    except KeyError as exc:
        raise ValueError(f"Unknown mode: {mode}. Valid modes: {', '.join(valid_modes())}") from exc


def resolve_env_value(value):
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1])
    return value
