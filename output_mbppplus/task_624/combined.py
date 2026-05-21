
def is_upper(string):
  return string.upper()


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['person'], ['final'], ['Valid'], [''], ['abcdefghijklmnopqrstuvwxyz'], ['He11o W0r1d!'], ['Thi5 is @ complex 1nput!'], ['Test1ng fUtur3'], ['I l0v3 c0d1ng!!'], ['H@ppy New Year 2022'], ['Th3 Qu1ck Br0wn F0x Jumps 0ver the L@zy D0g!'], ['@!$'], ['Thi5 is lnput!'], ['D0g!'], ['W0r1d!'], ['Thi5 is lnput!!'], ['l03'], ['l003'], ['Th3 Qu1ck Br0wn F0x Jumps 0veD0g!he L@zy D0g!'], ['YearHe1is1o We0r1d!'], ['cBr0wn0d1ng!!'], ['Thi5 @is @ complex 1nput!'], ['Thi5 @is @ comnplex 1nput!'], ['H@ppy New Yea0verr 2022'], ['F0x'], ['complelx'], ['lnput!F0x'], ['Qu1ck'], ['Thi5'], ['l00@is3'], ['@isQu1ck'], ['Th3 Qu1ck Br0wn F0xNew Jumps 0ver the L@zy D0g!'], ['c0d1ngg!!'], ['Thi5 lnput!!is lnput!!'], ['@!$Th3 Qu1ck Br0wn F0xNew Jumps 0ver the L@zy D0g!'], ['YearHe1is1oa We0r1d!'], ['Thi5 @is @ lnput!comnplex 1nput!'], ['D0g!cBr0wn0d1ng!!'], ['YearHe1is1o'], ['Yea0verr'], ['lnput!!'], ['c0d1ngg!!@is'], ['l0v3'], ['0ver'], ['YearHe1is1oa'], ['F0Thi5'], ['1nput!'], ['Th3 Qu1ck Br0wn F0xNew Jumps 0ver the L@zy D0g!Thi5'], ['D0g!Thi5'], ['c0d1Thi5Thi5 is lnput!! @is @ complex 1nput!ngg!!@is'], ['c0d1Thi5Tt!ngg!!@is'], ['compelx'], ['rrr'], ['I l0v3 c0Th3d1ng!!'], ['1nnput!'], ['Year'], ['2022'], ['abcdhijklmnopqrstuvwxyz'], ['YYea0verr'], ['New'], ['0W0r1d!'], ['Thi5 @is @ comnplrrrex 1nput!'], ['D0gTest1ng!cBr0wn0d1ng!!'], ['Test1ng efUtur'], ['@isQH@ppyu1ck'], ['Thi5 @is @ F0Thi5comnplrrresx 1nput!'], ['l0YearHe1is1oa We0r1d!0@is3'], ['c0d1Thiput!ngg!!@is'], ['Dg!g!'], ['Ye1nput!ngg!!@isarHYearHe1is1oae1is1o'], ['YearH1e1is1o We0r1d!'], ['Th3 Qu1ck Br0wn F0xNew Jumps 0ver the L@zy 0g!'], ['0W0r1d!0complelx'], ['Testur'], ['I l0veD0g!hed1ng!!'], ['Thi5 @is @ lnput!ccomnplrrrexomnplex 1nput!'], ['He11o'], ['YearHe1is1oa WeH0r1d!'], ['lnput!Fn0x'], ['Dc0d1ngg!!g!!g!'], ['1npu!'], ['He11o Wr0r1d!'], ['c0d1!ngg!!@is'], ['H@ppy New Year 2l0veD0g!hed1ng!!022'], ['YearHe1ioa'], ['abcdhijklmnopqrstuvwxyzYearHe1is1oa WeH0r1d!'], ['l0@is3'], ['YearHe1is1io'], ['l0v03'], ['D0Tg!Thi5'], ['0g!'], ['@isQcH@ppyu1ck'], ['Thi5 @is @ comt!'], ['YearH1e1is1o!'], ['OOoPGHemh'], ['lnp!!'], ['D0WeH0r1d!gTest1ng!cBr0wn0d1ng!!'], ['00veer'], ['rrrr'], ['Th3 Qu1ck He11oBr0wn F0xNew Jumps 0ver the L@zy D0g!'], ['r0Qu1cklx'], ['I'], ['fUtur3'], ['abcstuxvwxxyz'], ['T h3 Qu1ck Br0wn F0xNew Jumps 0ver the L@zy D0g!Thi5'], ['@!$Th3 Qu1ck Br0wn F0xNew Ju0g!'], ['@isQH@Yea0verrppyu1ck'], ['He11o Wr0r1Testur0W0r1d!d!'], ['NoCsH'], ['He1111o'], ['D0WHD0g!cBr0wn0d1ng!!0r1d!gTest1ng!cBr0wn0d1ng!!'], ['He11111o']]
result = []
for inp in inputs:
    result.append(is_upper(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
