
def catalan_number(num):
    if num <= 1:
         return 1   
    res_num = 0
    for i in range(num):
        res_num += catalan_number(i) * catalan_number(num - i - 1)
    return res_num


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[10], [9], [7], [0], [1], [2], [3], [True], [4], [False], [5], [6], [8], [11], [12], [13], [15], [14]]
result = []
for inp in inputs:
    result.append(catalan_number(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
