
import heapq as hq
def heap_sort(iterable):
    hq.heapify(iterable)
    return [hq.heappop(iterable) for _ in range(len(iterable))]


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [[[1, 3, 5, 7, 9, 2, 4, 6, 8, 0]], [[25, 35, 22, 85, 14, 65, 75, 25, 58]], [[7, 1, 9, 5]], [[]]]
result = []
for inp in inputs:
    result.append(heap_sort(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
