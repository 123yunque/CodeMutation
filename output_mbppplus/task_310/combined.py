
def string_to_tuple(str1):
    result = tuple(x for x in str1 if not x.isspace()) 
    return result


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['python 3.0'], ['item1'], ['15.10'], [''], ['hello   world'], ['çèêë'], ['   Hello World!   '], ['   '], ['1234567890'], ['abcdefghijklmnopqrstuvwxyz'], ['ABCDEFGHIJKLMNOPQRSTUVWXYZ'], ['MixedCase123'], ['        '], ['\n\t'], ['   15.10   '], ['item1, item2, item3'], ['item2,'], ['abcdefghijklmnopqrstkuvwxpyz'], ['whelloorld'], ['whellooWorld!d'], ['whelloorled'], ['Hello'], ['   Hello World!      '], ['   Hello World!      \n\t'], ['item3'], ['hello   worlld'], ['hçèêëello   worlld'], ['item3 '], ['abcd   Hello World!      efghijklmnopqrstuvwxyz'], ['hello   item3 world'], [' 10   '], ['ite'], ['hello   item3 15.10ld'], ['hello    wMixedCase123orld'], ['item1e,'], [' 1item3 0   '], ['çêë'], [' 100   '], ['hello 5  item3 15.10ld'], ['abcdefghhijklmnopqrstkuvwxpyz'], ['iteworlldm3'], ['05'], ['tite'], [' 100  efghijklmnopqrstuvwxyz'], ['055'], ['itemi3'], ['hello   wo 1item3 0   ld'], ['itemabcdefghwhelloorldhijklmnopqrstkuvwxpyz3 '], ['5ite'], ['    '], ['world'], ['   515.10   '], ['1 100   '], ['itemi33'], ['100'], ['çèwhelloorldêë'], ['çèwhelloorlldêë'], ['worlld'], ['çëitemi33'], ['1234wMixedCase123orld567890'], ['it33'], ['hçèêëello   whelloorldworlld'], ['abcdefghijitem1, item2, item3klmnopqrstuvwxyz'], ['abcd worlld  Hello World!      efghijklmnopqrstuvwxyz'], ['whelllooWorld!d'], ['item1, item2, iteem3'], ['hello   item3 15 .10ld'], ['10'], ['worworlldlld'], ['itemabcdefghwhelloorldhijklmnopqrstkuvwxpyz3'], ['ABCDEFGHIJKLMNOPQRSTUVWXY'], ['abcdefghijitem1, item2, iitem1,klmnopqrstuvwxyz'], ['   He  itemabcdefghwhelloorldhijklmnopqrstkuvwxpyz3 '], ['\n\n\t'], ['0whelloorled'], [' 1 0   '], ['hello   item3 15 .10l'], ['çêêë'], ['Mixe2dCase123'], ['whelllooWorldo!d'], ['   Hello World! tem3      \n\t'], ['hello   item3  15 .10ld'], ['ite10'], ['hello1234wMixedCase123orld567890   item3 15 .10l'], ['ABCDEFMNOPQRSTUVWXYZ'], ['hçèêëtiteello   whelloorldworlld'], ['whe    lloorlld'], ['tem3'], ['worl'], ['055item1,'], ['1'], ['12364567890'], ['hello1234wMixedCase123orld567890'], ['hçèêëello    Hello World! tem3      \n\t  worllld'], ['hello   item3 wor ld'], ['h4ello1234wMixedCase123orld567890   item3 15 .10l'], ['MixedCi'], ['15..10'], ['12364567890ite'], ['hello   item3t wor ld'], ['item3i3'], ['abcdefghijitem1, item2, iitelmnopqrstuvwxyz'], ['hello   item3 15 .1iitelmnopqrstuvwxyz0l'], ['.10hello   worldld'], ['h4ello1234wMixedCase123orld567890   itemtite.10l'], ['worldld'], ['abefghijklmnopqrstuvwxyz'], ['abcdefzghijklmnopqrstkuvwxpyz'], ['QkkSNfeX'], ['hçèêëtiteello'], ['hello    wMixeodCase123orld'], ['imtemi3'], [' 110   '], ['.10ldMisxe2dCase123'], [' 10   1234567890']]
result = []
for inp in inputs:
    result.append(string_to_tuple(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
