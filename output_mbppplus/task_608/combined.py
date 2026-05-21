
def bell_Number(n): 
    bell = [[0 for i in range(n+1)] for j in range(n+1)] 
    bell[0][0] = 1
    for i in range(1, n+1):
        bell[i][0] = bell[i-1][i-1]
        for j in range(1, i+1): 
            bell[i][j] = bell[i-1][j-1] + bell[i][j-1] 
    return bell[n][0] 


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[2], [3], [4], [10], [20], [30], [50], [100], [9], [29], [31], [32], [11], [101], [12], [98], [82], [49], [81], [19], [99], [83], [True], [8], [13], [28], [False], [21], [15], [22], [23], [24], [27], [14], [102], [97], [80], [16], [7], [103], [18], [6], [33], [25], [34], [5], [35], [17], [73], [36], [84], [51], [52], [53], [26], [96], [72], [48], [68], [57], [74], [93], [58], [54], [67], [95], [79], [78], [92], [55], [104], [0], [46], [47], [39], [75], [71], [56], [70], [37], [105], [42], [85], [45], [91], [38], [1], [66], [43], [40], [41], [44], [106], [69], [94], [65], [90], [59], [107], [86], [76], [64], [87], [108], [88]]
result = []
for inp in inputs:
    result.append(bell_Number(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
