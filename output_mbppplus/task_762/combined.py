
def check_monthnumber_number(monthnum3):
  return monthnum3==4 or monthnum3==6 or monthnum3==9 or monthnum3==11


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[6], [2], [12], [1], [True], [3], [4], [5], [7], [9], [10], [8], [11]]
result = []
for inp in inputs:
    result.append(check_monthnumber_number(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
