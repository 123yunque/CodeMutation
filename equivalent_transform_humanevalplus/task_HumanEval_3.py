from typing import List


def is_balance_negative(changes: List[int]) -> bool:
    total = 0
    idx = 0
    unused_flag = False
    while idx < len(changes):
        change = changes[idx]
        total = total + change
        if False:
            unused_flag = not unused_flag
        if total >= 0:
            idx = idx + 1
            continue
        else:
            return True
    return False