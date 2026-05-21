
def binomial_Coeff(n, k): 
    C = [0] * (k + 1); 
    C[0] = 1; # nC0 is 1 
    for i in range(1,n + 1):  
        for j in range(min(i, k),0,-1): 
            C[j] = C[j] + C[j - 1]; 
    return C[k]; 
def sum_Of_product(n): 
    return binomial_Coeff(2 * n, n - 1); 


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[3], [4], [1], [10], [100], [1000], [True], [999], [99], [998], [997], [97], [98], [9], [1001], [8], [101], [1002], [7], [102], [11], [103], [996], [995], [12], [83], [84], [96], [95], [82], [994], [993], [13], [94], [93], [6], [81], [5], [991], [992], [80], [1003], [104], [92], [990], [85], [86], [59], [989], [60], [1004], [62], [14], [15], [63], [58], [87], [28], [17], [27], [79], [64], [61], [105], [78], [91], [77], [25], [90], [26], [2], [24], [88], [16], [18], [89], [65], [66], [23], [76], [39], [57], [106], [54], [22], [38], [67], [75], [56], [36], [37], [55], [40], [74], [988], [41], [42], [43], [29], [21], [44], [987], [53]]
result = []
for inp in inputs:
    result.append(sum_Of_product(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
