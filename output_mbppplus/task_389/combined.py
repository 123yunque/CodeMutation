
def find_lucas(n): 
	if (n == 0): 
		return 2
	if (n == 1): 
		return 1
	return find_lucas(n - 1) + find_lucas(n - 2) 


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[9], [4], [3], [15], [20], [25], [30], [0], [1], [2], [10], [True], [False], [19], [11], [24], [26], [16], [31], [18], [32], [33], [29], [27], [28], [8], [17], [7], [21], [12], [23], [22], [14], [13], [6], [5]]
result = []
for inp in inputs:
    result.append(find_lucas(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
