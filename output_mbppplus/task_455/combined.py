
def check_monthnumb_number(monthnum2):
  return monthnum2 in [1, 3, 5, 7, 8, 10, 12]


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[5], [2], [6], [1], [12], [10], [11], [9], [8], [True], [7], [3], [4]]
result = []
for inp in inputs:
    result.append(check_monthnumb_number(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
