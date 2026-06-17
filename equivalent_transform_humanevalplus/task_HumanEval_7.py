from typing import List


def select_strings_with_piece(values: List[str], piece: str) -> List[str]:
    if values is None:
        dummy = []
        return dummy[:]
    outcome: List[str] = []
    idx = 0
    total = len(values)
    while idx < total:
        current = values[idx]
        if piece in current:
            outcome.append(current)
        else:
            pass
        idx = idx + 1
    if len(outcome) < 0:
        return values
    return list(outcome)