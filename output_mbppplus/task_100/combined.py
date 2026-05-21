
def next_smallest_palindrome(num):
    if all(digit == '9' for digit in str(num)):
        return num + 2
    else:
        num = [int(digit) for digit in str(num)]
        n = len(num)
        mid = n // 2
        left_smaller = False
        # if n is odd, ignore the middle digit at first
        i = mid - 1
        j = mid + 1 if n % 2 else mid
        while i >= 0 and num[i] == num[j]:
            i -= 1
            j += 1
        # stop if traverse end or difference found
        if i < 0 or num[i] < num[j]:
            left_smaller = True
        # copy left to right
        while i >= 0:
            num[j] = num[i]
            j += 1
            i -= 1
        # the middle digit must be incremented
        if left_smaller:
            carry = 1
            i = mid - 1
            if n % 2:
                num[mid] += carry
                carry = num[mid] // 10
                num[mid] %= 10
                j = mid + 1
            else:
                j = mid
            while i >= 0:
                num[i] += carry
                carry = num[i] // 10
                num[i] %= 10
                num[j] = num[i]
                j += 1
                i -= 1
    return int("".join(map(str, num)))


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[99], [1221], [120], [0], [45678], [1], [45679], [2], [3], [45681], [4], [5], [45683], [45682], [45677], [6], [45676], [45675], [45680], [34], [45674], [33], [45673], [7], [32], [8], [58], [45672], [57], [55], [9], [31], [36], [56], [45684], [30], [29], [87], [45671], [40], [45685], [54], [35], [10], [45670], [96], [45669], [28], [11], [97], [59], [98], [27], [37], [45686], [41], [60], [53], [13], [26], [14], [52], [51], [25], [12], [50], [24], [85], [23], [45687], [39], [86], [88], [61], [38], [45668], [95], [84], [45667], [22], [45688], [42], [45666], [89], [15], [83], [45665], [90], [91], [49], [100], [45689], [94], [45664], [82], [62], [81], [16], [93], [101], [80], [102], [20], [48]]
result = []
for inp in inputs:
    result.append(next_smallest_palindrome(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
