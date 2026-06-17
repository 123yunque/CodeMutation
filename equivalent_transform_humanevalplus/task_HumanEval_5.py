from typing import List


def intersperse(sequence: List[int], delimeter: int) -> List[int]:
    dummy_flag = False
    if dummy_flag:
        return []  # unreachable
    container: List[int] = list()
    length = len(sequence)
    idx = 0
    while idx < length:
        current = sequence[idx]
        container.append(current)
        if not (idx == length - 1):
            container.append(0 + delimeter)
        idx += 1
    return container