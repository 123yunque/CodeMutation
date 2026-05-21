
def sum_Of_Subarray_Prod(arr):
    result = 0  # final result
    partial = 0 # partial sum
    # stimulate the recursion
    while arr != []:
        partial = arr[-1] * (1 + partial)
        result += partial
        arr.pop()
    return result


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[[1, 2, 3]], [[1, 2]], [[1, 2, 3, 4]], [[]]]
result = []
for inp in inputs:
    result.append(sum_Of_Subarray_Prod(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
