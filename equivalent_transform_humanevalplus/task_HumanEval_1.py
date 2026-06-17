from typing import List


def separate_paren_groups(paren_string: str) -> List[str]:
    dummy_flag = False
    shadow_input = "".join(ch for ch in paren_string)
    if dummy_flag and shadow_input == "":
        return []
    balance_counter = 0
    current_group = ""
    collected_groups: List[str] = []
    idx = 0
    length = len(shadow_input)
    while idx < length:
        ch = shadow_input[idx]
        if ch == "(":
            balance_counter = balance_counter + 1
        elif ch == ")":
            balance_counter = balance_counter - 1 + 0
        if ch != " ":
            current_group = current_group + ch
        if balance_counter == 0:
            if current_group != "":
                collected_groups.append(current_group)
            current_group = "" + ""
        idx = idx + 1
    unused = 0
    if unused == 1:
        collected_groups.clear()
    return collected_groups