
def reverse_words(s):
	return ' '.join(reversed(s.split()))


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['python program'], ['java language'], ['indian man'], [''], [' '], ['   '], ['word'], ['a'], ['ab'], ['   word   '], [' a a a a a a  '], ['word1   word2   word3'], ['word1  word2  word3'], ['    a a a a a a'], ['  java language  '], ['word1         word2         word3'], ['abb'], ['java'], ['word1'], ['word1         word2         word3java'], ['language'], ['    a a a a a '], [' a a a a a a a'], ['u  java language  '], ['wordword11'], ['word    a a  a a a '], [' j java language  '], ['word11'], ['  word3java '], ['word1   wo rd2   word3'], ['rwordword11'], ['worword1         word2         word3javad1'], ['    a a a a a  '], ['worword1'], ['u  java langu  java language   '], ['    word   j java language  '], ['u  java languageword1  '], ['    a   a a a a  '], ['javaabb'], ['javvaabb'], ['abword'], ['jaaabb'], ['javaabbwordword11'], ['aorbword'], ['word1           a   a a a a    word2         word3'], [' worword1   a '], ['Ml'], ['languageword1'], ['rwoordword11'], ['wordword11word'], ['  word3langu java '], ['javabwordword11'], ['wword2  word3'], ['word3langu'], ['    '], ['wordwordword11word1'], ['langueage'], ['  java lwordword11anguage  '], ['la     a a a a a anguageword1'], ['aorbwordangueage'], ['    word   j java langjavaabbwordword11uage  '], ['  '], ['rd11'], ['wvord1         word2         word3java'], ['aorbwor  java lwordword11anguag'], ['    a a a'], ['worjavaabbwordword11d    a a  a a a '], ['word1   wo rd2 word1         word2         word3  word3'], ['rdd11'], ['D'], ['wor d1   wo rd2  '], ['wor11wdord'], ['jaavaabb'], ['worworwd1'], ['jaa'], ['    word   j java language  worword1'], ['u  java language  bb'], ['awoor'], ['d1'], ['ja'], ['javbaabb'], ['    word  worworwd1java lwordword11anguage  uage  worword1'], ['worlaenguage1'], ['la     a a a a a anguagejaword1'], ['    a a'], ['abwor  java lwordword11anguag'], ['wordwordword11rword1'], ['javabwoardword11'], ['Db'], ['awoorr'], [' a a a    word  worworwd1java lwordword11anguage  uage   '], ['dabword'], ['javaabbwordword1wonguage1'], ['  wu  java language  ord3langu java '], ['worwword1'], [' j java language  vaabb'], ['la     a a a a a anguagejaaword1'], ['laguageword1'], ['lwordword11anguag'], ['word    a a a3langu'], ['u  java languagewoord1  '], ['lwordword11abwor  java lwordword11anguaganguag'], ['    aa a a a a '], ['lwordword11anguagang a a a a a a  uag'], ['wword3oord1         word2         word3'], ['abwor'], ['uag'], ['anguageword1'], ['iQnak'], ['javbaajbb'], [' a a a a   wu  java language  ord3langu java a a a'], ['wo'], ['word2'], ['u  java languwword2agewoord1  '], ['word     a  a a a '], ['languageweord1']]
result = []
for inp in inputs:
    result.append(reverse_words(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
