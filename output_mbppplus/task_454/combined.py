
import re
def text_match_wordz(text):
        return 'z' in text


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['pythonz.'], ['xyz.'], ['  lang  .'], ['*z@'], ['1234z5678'], ['z x z'], ['x'], [''], ['*z@*z@'], ['*z'], ['**z@'], ['**zz@'], ['*z x z*zz@'], ['*x*z@*z@z'], ['***z@'], ['z'], ['x****z@'], ['*z xz x z z*zz@'], ['z*zz@'], ['*@*z@'], ['***@'], ['***zz@@x****z@'], ['*x*z@*z@'], ['*z xzz x z z*zz@'], ['z*z@'], ['**z'], ['*@'], ['*@*z@@'], ['z*zz@z'], ['*@**z@'], ['****@'], ['****z@'], ['*zz'], ['***zz@@x*****z@'], ['z*zz@z*zz@z'], ['z*zz@z*zzz@z'], ['****z*z@z@@x****z@'], ['**zx*z@*z@'], ['*x@*z@'], ['z*****z@zz@z*zz@z'], ['*****@*z'], ['n'], ['**@*z@@'], ['z**z@'], ['*zzz*@z'], ['***@@'], ['z****z@'], ['*z@*z****z@z'], ['****z@*zzz*@z'], ['**z****z*z@z@@x****z@z@'], ['*zzz*z'], ['****z@*zzz*z****z@@z*z@**z@'], [' z  x z'], ['z**@*z@zz@z*zz@z'], ['*z@*z@**zz'], ['*zz xzz x z z*zz@'], ['*z *zz x zz x z z*zz@z*zz@'], ['z**z@*z@zz@z*zz@z'], ['**zx*z@*z*@'], ['z*zzz@'], ['*'], ['z*zz@zz'], ['z**zz@'], ['*z x*x@*z@zz  z*zz@'], ['1234z56n78'], ['z*zzzz@'], ['zzz'], ['**@@x*****z@'], ['**zx*z@*z*@x'], ['***z**z@@@*z@'], ['xz'], ['*zz xzz x z z*z'], ['1234z566n78'], ['z*zz@z*z*zz@z*zzz@zzzz@z'], ['z**@*z@ z  x zzz@z*zz@z'], ['1234z78'], ['zz'], ['*x*z@*zz@'], ['x*x@*z@zz'], ['**zz xzz x z z*z'], ['z**z**zz@'], ['z*zz@***z@'], ['z***zz@z@'], ['12334z78'], ['*z zzz'], ['*@@'], ['yVHKcHlY'], ['z*zz@***z@x*zz xzz x z z*z'], ['*z  x z*zz@'], ['z*zz@z*zz@*@*z@@'], ['*@***z'], ['JlGWYIid'], ['*****@'], ['zyVHKcHlY x z'], ['@*@*z@'], ['****z@*zzz*@zz'], ['*zzz***z x*x@*z@zz  z*zz@*z@z'], ['12314z566n78'], ['z*****z@'], ['12314z566n78*z x*x@*z@zz  z*zz@'], ['l'], ['*z@*z*z x*x@*z@zz  z*zz@****z@z'], ['*x@*zz@'], ['********z@*zzz*@zz'], ['****z@*zzz*z*@@z*z@**z@'], ['1234z566nl78']]
result = []
for inp in inputs:
    result.append(text_match_wordz(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
