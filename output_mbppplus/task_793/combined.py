
def last(arr,x):
    return len(arr)-arr[::-1].index(x) - 1


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[[1, 2, 3], 1], [[1, 1, 1, 2, 3, 4], 1], [[2, 2, 3, 3, 6, 8, 9], 3]]
result = []
for inp in inputs:
    result.append(last(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
