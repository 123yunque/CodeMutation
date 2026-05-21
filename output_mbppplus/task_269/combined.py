
def ascii_value(k):
  return ord(k)


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['A'], ['R'], ['S'], ['@'], ['®'], ['!'], [' '], ['ص'], ['&'], ['\n'], ['€'], ['^'], ['ä'], ['π'], ['~'], ['\t'], ['©'], ['๑'], ['$'], ['7'], ['%'], ['['], ['{'], ['é'], ['\x00'], ['\x1d'], ['♥'], ['\uffff'], ['\x7f'], ['\x80'], ['™'], ['文'], ['→'], ['F'], ['q'], ['E'], ['o'], ['W'], ['U'], ['O'], ['K'], ['v'], ['Z'], ['N'], ['P'], ['b'], ['y'], ['l'], ['V'], ['D'], ['u'], ['s'], ['I'], ['h'], ['H'], ['B'], ['k'], ['X'], ['L'], ['p'], ['Y'], ['c'], ['J'], ['T'], ['a'], ['e'], ['r'], ['G'], ['j'], ['m'], ['z'], ['n'], ['g'], ['t'], ['i'], ['d'], ['M'], ['x'], ['f'], ['C'], ['Q'], ['w']]
result = []
for inp in inputs:
    result.append(ascii_value(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
