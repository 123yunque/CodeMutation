
def bell_number(n):   
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

inputs = [[2], [10], [56], [0], [100], [99], [True], [False], [98], [1], [3], [97], [96], [11], [12], [92], [95], [94], [14], [13], [55], [17], [15], [93], [16], [9], [91], [54], [25], [18], [4], [5], [6], [8], [90], [53], [7], [19], [64], [20], [21], [63], [52], [24], [57], [22], [62], [89], [51], [50], [88], [58], [49], [45], [65], [23], [87], [46], [59], [26], [44], [61], [48], [47], [60], [30], [27], [86], [28], [31], [29], [66], [67], [85], [70], [71], [43], [69], [82], [83], [72], [68], [81], [73], [32], [33], [42], [74], [84], [41], [80], [79], [75], [40], [76], [34], [35], [78], [77], [39], [38], [36]]
result = []
for inp in inputs:
    result.append(bell_number(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
