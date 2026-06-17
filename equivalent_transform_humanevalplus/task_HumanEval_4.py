from typing import List


def mean_absolute_deviation(values: List[float]) -> float:
    _unused_flag = False
    if _unused_flag:
        return 0.0
    total = 0.0
    count = 0
    for v in values:
        total = total + v
        count = count + 1
    avg = total / count
    abs_sum = 0.0
    idx = 0
    length = len(values)
    while idx < length:
        current = values[idx]
        abs_sum = abs_sum + (current - avg if current >= avg else avg - current)
        idx = idx + 1
    return abs_sum / length