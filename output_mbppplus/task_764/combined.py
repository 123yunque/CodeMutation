
def number_ctr(s):
    return sum(c.isdigit() for c in s)


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['program2bedone'], ['3wonders'], ['123'], ['3wond-1ers2'], [''], ['hello world'], ['1234567890'], ['1 2 3'], ['      '], ['12 2 3'], ['hello 12 2 3world'], ['lhello world'], ['12 2  3'], ['lhello'], ['1 22 3'], ['22'], ['1 2 3lhello'], ['hello 12 2 olrld'], ['lhell3lhelloo world'], ['3'], ['1 22 322'], ['helhello 12 2 olrldlo world'], ['hello'], ['1lhell3lhelloo 22 3'], ['3world'], ['12 22 322'], ['2222'], ['1 22 3212'], ['hello 12 2 olrlld'], ['world'], ['1 22 13212'], ['112 2  3'], ['1lhell3lhell oo 22 3'], ['322'], ['helhello 12 2 olrldlo worldolrlld'], ['     olrldlo '], ['112'], ['olrlld'], ['12'], ['olrld'], ['1 2 2 3'], ['       '], ['oo'], ['122  3'], ['112 2  32233world'], ['1 2 3lheworldllo'], ['olrldlo'], ['olr'], ['hello 12 2 olrlld2222'], ['hello 12l 2 olrld'], ['old'], ['lhello worlolrlld222o2d'], ['1lhell3lhell'], ['wold'], ['22122  3'], ['ooo'], ['lhewll3lhelloo world'], ['1hello 12l 2 olrld 23 3'], ['olrlld2222'], ['1lhell3l13212hell'], ['13212lhell3lhellolo'], ['1 22 31 2 3212'], ['rw'], ['lhello122  3'], ['              '], ['ollrlld2222'], ['1 22 33'], ['1123'], ['3lhello1234567890'], ['31'], ['1lhell3lhelloo 222 3'], ['helhello'], ['bNEygn'], ['2lhell3lhelloo22'], ['        '], ['lhell3lhelloo weorld'], ['12 2 122  33'], ['1 22'], ['12 2 122  233'], ['        olrlld'], ['lhell3lhelloollo'], ['helhelllo'], ['233'], ['222'], ['12 2 122lhewll3lhelloo worldlhell3lhelloo  33'], ['3w12 2 122  33orld'], ['1l12 2  32 122lhewll3lhelloo worldlhell3lhelloo  33l oo 22 3'], ['1 32222 3212'], ['3lheworldllo'], ['lhdello worlolrlld222o2d'], ['122'], ['1l12 2  32 122lhewll3lhellloo worldlhell3lhelloo  33l oo 22 3'], ['31hello 12 2 olrlld2222'], ['1  22'], ['1l12'], ['worldolrlld'], ['hell3lhello1234567890o2222'], ['olrlld22d22'], ['3wold'], ['22122'], ['ollrll12 2 122  233d2222'], ['3123'], ['122 2 3'], ['1l12 2  3e2 122lhewll3lhellloo wohello 12l3lhelloo  33l oo 22 3'], ['hell3lhello1234567890o22223'], ['12 lhello1222 3'], ['hello 12 2 orld'], ['wworld']]
result = []
for inp in inputs:
    result.append(number_ctr(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
