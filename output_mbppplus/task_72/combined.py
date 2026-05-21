
def dif_Square(n): 
    # see https://www.quora.com/Which-numbers-can-be-expressed-as-the-difference-of-two-squares
    return n % 4 != 2


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[5], [10], [15], [991], [567], [13], [24], [568], [992], [569], [990], [566], [True], [989], [25], [14], [565], [23], [988], [12], [11], [16], [17], [993], [564], [563], [22], [994], [9], [21], [995], [996], [20], [18], [997], [8], [987], [45], [562], [570], [26], [561], [998], [19], [77], [7], [76], [560], [986], [27], [44], [571], [28], [75], [46], [78], [74], [985], [29], [572], [984], [73], [983], [79], [573], [47], [50], [982], [981], [71], [49], [80], [51], [999], [30], [81], [6], [1000], [980], [1001], [1002], [82], [1003], [52], [574], [53], [1004], [70], [575], [69], [576], [979], [83], [72], [68], [43], [89], [42], [977], [33], [4], [36], [978], [3]]
result = []
for inp in inputs:
    result.append(dif_Square(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
