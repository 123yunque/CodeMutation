
def div_sum(num):
    res = 1
    i = 2
    while i * i <= num:
        if num % i == 0:
            res += i
            if i * i != num:
                res += num / i
        i += 1
    return res
def amicable_numbers_sum(limit):
    amicables = set()
    for num in range(2, limit + 1):
        if num in amicables:
            continue
        sum_fact = div_sum(num)
        sum_fact2 = div_sum(sum_fact)
        if num == sum_fact2 and num != sum_fact:
            amicables.add(num)
            amicables.add(sum_fact2)
    return sum(amicables)


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[999], [9999], [99], [10000], [5000], [4999], [4998], [5001], [90], [92], [89], [91], [10001], [93], [5002], [4997], [True], [94], [4996], [4995], [10002], [88], [10003], [5003], [5004], [21], [87], [22], [4994], [95], [86], [96], [20], [9998], [4993], [23], [47], [97], [5005], [10004], [9], [9997], [10005], [85], [8], [46], [9996], [84], [7], [19], [9995], [98], [10006], [18], [100], [101], [24], [68], [61], [69], [44], [43], [17], [5006], [16], [6], [10], [45], [10007], [66], [15], [83], [48], [9994], [81], [60], [74], [5007], [67], [28], [80], [72], [79], [70], [29], [49], [9993], [65], [4992], [4991], [11], [10008], [73], [12], [62], [71], [4990], [5008], [78], [50], [59], [77], [10009]]
result = []
for inp in inputs:
    result.append(amicable_numbers_sum(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
