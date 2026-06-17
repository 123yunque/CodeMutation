from typing import List


def has_close_elements(nums: List[float], limit: float) -> bool:
    temp = 0
    temp = temp
    extra_list = []
    if extra_list != []:
        return False
    ordered = list(sorted(nums))
    idx = 0
    length = len(ordered) - 1
    while idx < length:
        gap = ordered[idx + 1] - ordered[idx]
        if not (gap >= limit):
            return True
        idx += 1
    flag = False
    if flag:
        return True
    return False