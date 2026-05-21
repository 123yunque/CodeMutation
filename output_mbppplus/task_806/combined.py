
def max_run_uppercase(test_str):
  cnt = 0
  res = 0
  for idx in range(0, len(test_str)):
    if test_str[idx].isupper():
      cnt += 1
    else:
      res = cnt
      cnt = 0
  if test_str[len(test_str) - 1].isupper():
    res = cnt
  return res


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['GeMKSForGERksISBESt'], ['PrECIOusMOVemENTSYT'], ['GooGLEFluTTER'], ['A'], ['a'], ['aa'], ['aA'], ['Aaa'], ['aaaAaA'], ['aaaAaAA'], ['aaaA'], ['aaA'], ['aAaa'], ['aaaaA'], ['AaaA'], ['aaaAaaaAaAA'], ['aAaaa'], ['aaaAAaA'], ['AaaaAA'], ['aaaaAaAA'], ['AaaaAAA'], ['aaaaAaA'], ['AaaaaAA'], ['Aa'], ['aaaAaaaaaAAA'], ['aaaAAaaaaaAAaaaAAaAA'], ['aaaaAAaA'], ['aAaaaaAAaaaaAAA'], ['aaaaaAAaA'], ['aaaaaAaAAaaAAaA'], ['aaaaAAaAA'], ['xTzcVWVVy'], ['aaaaAAaAAAaaA'], ['aaAaaaAAaA'], ['aaaaaAaAAaaAaAaA'], ['aaaaAaaaAaAA'], ['AaaaAAaA'], ['AAa'], ['aaaaaAaAAaaAAaAA'], ['AaAa'], ['AaaaaAAA'], ['aaaaaAAaAAAaa'], ['aaAaaaAAAaaAAaAA'], ['xTzcVWVaaaAAaaaaaAAaaaAAaAAy'], ['aaaaAaAaAaa'], ['aaaaAaaaaaAaAaAaaA'], ['AaaaaAAaaaaaAAaaaAAaAAaaAAA'], ['aaaaaAaAAaaaAAaA'], ['aaaaAaaAAaA'], ['aaAaaaAaaAAaAA'], ['aaaAA'], ['aAaAaaA'], ['aaaAAaaaaaAAaaAaAAaAA'], ['AaaaaA'], ['AAAa'], ['aaaAAAaaaAaaAAaA'], ['aaAaaaaAAAaaAAaAA'], ['aaaaAaAAaa'], ['aaa'], ['aaaAAaaaaaAAaAaAaAAaaAaaaAAAaaAAaAAaAA'], ['aaaaAaaaaAAAaaAAaA'], ['aaAaaaAAAaaAAaAAaaAaaaAaA'], ['AaaaaAAaaaaaAAaAaAaAAaaAaaaAAAaaAAaAAaAAaA'], ['aaaAaaaAaaaaaAAAaAA'], ['aaaaaAaaaaaAAAAaaaaAAAaaAAaAA'], ['aaaaaaaaAaAAaaAaAaAaaAaAAaaAAaA'], ['aaaaAaaaaaAaAAaaAAaA'], ['aaaaaAaAAaa'], ['aaaaaAaaaaAaAAaaaAAaaaAAaA'], ['aaaAAaaaaaAAAaAaAaAAaaAaaaAAAaaAAaAAaAA'], ['aaAaaaAAAaaAAAaAA'], ['aaaaaaaaAaAAaaAaAaAaaAaaaaAAaAAaAAaaAAaaaaAAaAaaaaA'], ['aaaaaAaaaAaAA'], ['aaaaAaaaaaAaaaaaAAAAaaaaAAAAaAA'], ['aaaaAAaaaaaAAaaAaAAaAA'], ['AAaaaAAaA'], ['AAaaaaAAaA'], ['AAaaaA'], ['aAaaaaAAaAaaA'], ['aaaaAaAAaaaAAa'], ['aaaaaaaaaaAaaaAAAaaAAaAAAaAAaaAaAaaaaAAaaaaA'], ['aaaaaAaaaaAAAaaAAaA'], ['aaaAAaaaaAAA'], ['aAaaaAAaAAAaaA'], ['AaAaaaaAA'], ['aaaaaaaAaaaaAaAAaaaAAaaaAAaAaAA'], ['AaAaaaaAAAaA'], ['xzcVWVVy'], ['AaAaAaaaAAAaA'], ['aaaaAaaa'], ['aaaaaA'], ['aaaaaaaaAaAAaaAaAaAaaAaaaaAAaAAaAAaaAAaaaaAAaAAAaaAaaaaAAaAaaaaA'], ['aaaaAaaaaaAaAaAaaAaaaAAaaaaaAAaAaAaAAaaAaaaAAAaaAAaAAaAA'], ['aaaAaaaaAAAaaAAaAA'], ['aaaaaaaAaAaAaaAAaaaaAAA'], ['aAaaaaAAaaaaAA'], ['aaaAAaaaaaAAaaaAAaAAaaaaaAaaaAaAA'], ['AaaaA'], ['AaAaA'], ['AaaaaAAAa'], ['aAaAaaaAA'], ['AaA'], ['aaaAaaaAaaaaaAAAaAAA'], ['aAAaaaAA'], ['aaaAAaaaaaaaaAAaaaaaAAAaAaAaAAaaAaaaAAAaaAAaAAaAAAAaaaAAaAAaaaaaAaaaAaAA']]
result = []
for inp in inputs:
    result.append(max_run_uppercase(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
