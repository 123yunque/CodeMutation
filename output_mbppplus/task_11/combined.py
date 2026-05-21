
def remove_Occ(s,ch): 
    s = s.replace(ch, '', 1)
    s = s[::-1].replace(ch, '', 1)[::-1]
    return s 


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['hello', 'l'], ['abcda', 'a'], ['PHP', 'P'], ['a', 'a'], ['aaa', 'a'], ['hello world', 'x'], ['worlda', 'a'], ['x', 'x'], ['hello world', 'a'], ['world', 'x'], ['xx', 'x'], ['xworlaaada', 'x'], ['axworlaaada', 'x'], ['waaaorlda', 'a'], ['xhello world', 'a'], ['xxx', 'x'], ['worlda', 'x'], ['world', 'a'], ['hwllo world', 'a'], ['axx', 'a'], ['hwllo world', 'x'], ['hwllo', 'a'], ['hwl', 'a'], ['ahwllo world', 'a'], ['xxx', 'a'], ['hwll', 'a'], ['hhwl', 'a'], ['ahwllo', 'x'], ['whwlloorld', 'a'], ['wda', 'x'], ['hwl', 'x'], ['xrworlaaada', 'x'], ['aahwllo', 'a'], ['a', 'x'], ['xxwaaaorlda', 'x'], ['wda', 'a'], ['hxworlaaadawllo', 'a'], ['aaaa', 'a'], ['xrworworldalaaadax', 'x'], ['aaawda', 'x'], ['hello worldx', 'x'], ['xrworworldalaaadax', 'a'], ['xrworlaaadaworldx', 'x'], ['aahwllo', 'x'], ['xworlaaadaaaaa', 'a'], ['xxxx', 'a'], ['xhello worlda', 'a'], ['xrworworaldalaaadax', 'a'], ['xaaaa', 'x'], ['xxwaahello worldxaorlda', 'x'], ['axworlaaada', 'a'], ['worldxaorlda', 'x'], ['hellloa', 'a'], ['xaaa', 'x'], ['aa', 'a'], ['xhello', 'a'], ['xrworlaaaada', 'x'], ['axxxaawda', 'x'], ['hello worldxxhello worlda', 'a'], ['xhello', 'x'], ['hxworlaaadawlolo', 'a'], ['aa', 'x'], ['lo', 'x'], ['xaaaa', 'a'], ['waaaorllda', 'a'], ['ahwllao', 'x'], ['aaa', 'x'], ['xxhello', 'x'], ['wdaa', 'a'], ['xrworworaldalaaadaxa', 'a'], ['waaaorlxxwaaaorlda', 'a'], ['aahwllao', 'x'], ['hello worldx', 'a'], ['lo', 'a'], ['hellloa', 'x'], ['helwdalloa', 'x'], ['worldxxhellox', 'x'], ['hello', 'x'], ['l', 'x'], ['waaaorlldalo', 'x'], ['xrwax', 'x'], ['waaaorllda', 'x'], ['whwlloorld', 'x'], ['aahhwla', 'x'], ['waaaorlda', 'x'], ['llo', 'l'], ['axaahwllaoworlaaada', 'a'], ['hwllor world', 'a'], ['xworlaaadaaaaa', 'x'], ['waaaorlldal', 'a'], ['aahawllao', 'x'], ['lllo', 'l'], ['worlaaaadxaorlda', 'x'], ['hello worldxxhhelloworlda', 'a'], ['hwlll', 'a'], ['xrworwoxxxraldalaaadaxa', 'a'], ['ll', 'x'], ['aaahwllaoo', 'a'], ['worldx', 'a'], ['xrworworaldalaaadaxa', 'x'], ['hxworlaaadawlolo', 'x'], ['whello world', 'x'], ['ahwllo', 'a'], ['ahxworlaaadawlolo', 'a'], ['whello', 'x'], ['ax', 'a']]
result = []
for inp in inputs:
    result.append(remove_Occ(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
