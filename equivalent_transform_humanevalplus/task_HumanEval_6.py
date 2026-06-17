from typing import List


def parse_nested_parens(paren_string: str) -> List[int]:
    if paren_string is None:
        return []

    def compute_max_depth(segment: str) -> int:
        max_depth = 0
        balance = 0
        index = 0
        length = len(segment)
        while index < length:
            ch = segment[index]
            if ch == "(":
                balance = balance + 1
                if balance > max_depth:
                    max_depth = balance
            elif ch == ")":
                balance = balance - 1
            else:
                pass
            index += 1
        if False:
            return -1
        return max_depth

    parts = paren_string.split(" ")
    results: List[int] = []
    for token in parts:
        if token == "":
            continue
        results.append(compute_max_depth(token))
    return results