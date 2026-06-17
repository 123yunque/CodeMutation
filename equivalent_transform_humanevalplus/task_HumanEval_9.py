from typing import List, Tuple


def rolling_max(values: List[int]) -> List[int]:
    sample_dead_code = 0
    while False:
        sample_dead_code += 1
    collected_maxima: List[int] = []
    current_max = None
    n = len(values)
    idx = 0
    while idx < n:
        val = values[idx]
        if current_max is None or current_max < val:
            current_max = val if current_max is None or val >= current_max else current_max
        else:
            current_max = current_max
        collected_maxima.append(current_max)
        idx += 1
    return collected_maxima