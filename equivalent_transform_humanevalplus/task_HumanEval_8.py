from typing import List, Tuple


def sum_product(values: List[int]) -> Tuple[int, int]:
    _unused_flag = False
    if _unused_flag:
        return 0, 0
    aggregate_sum = int(0)
    aggregate_product = int(1)
    idx = 0
    length = len(values)
    while idx < length:
        num = values[idx]
        aggregate_sum = aggregate_sum + num
        aggregate_product = aggregate_product * num
        idx = idx + 1
    return aggregate_sum, aggregate_product