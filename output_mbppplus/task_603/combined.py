
def get_ludic(n):
	ludics = []
	for i in range(1, n + 1):
		ludics.append(i)
	index = 1
	while(index != len(ludics)):
		first_ludic = ludics[index]
		remove_index = index + first_ludic
		while(remove_index < len(ludics)):
			ludics.remove(ludics[remove_index])
			remove_index = remove_index + first_ludic - 1
		index += 1
	return ludics


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[10], [25], [45], [100], [1000], [10000], [999], [9999], [True], [9998], [101], [102], [998], [9997], [997], [99], [10001], [1001], [103], [10002], [104], [996], [995], [9996], [61], [31], [60], [32], [106], [9995], [9994], [9993], [105], [1002], [62], [33], [1003], [59], [107], [58], [15], [57], [30], [81], [16], [69], [34], [70], [27], [51], [29], [71], [35], [50], [79], [108], [56], [10003], [72], [63], [17], [49], [9992], [10004], [10005], [68], [80], [36], [64], [109], [88], [82], [47], [66], [10006], [55], [78], [28], [1004], [67], [41], [91], [87], [48], [18], [9991], [5], [54], [76], [110], [85], [97], [52], [84], [96], [90], [86], [994], [9990], [6], [83], [77], [95], [89], [19], [42]]
result = []
for inp in inputs:
    result.append(get_ludic(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
