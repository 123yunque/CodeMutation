
def all_Characters_Same(s) :
    return all(ch == s[0] for ch in s[1:])


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['python'], ['aaa'], ['data'], [''], ['ms'], ['mms'], ['msms'], ['mmms'], ['yQNKBeQ'], ['msmyQNKBeQs'], ['mmss'], ['m'], ['msmss'], ['msmyQNyQNKBeQKBeQs'], ['mmsss'], ['mmsmyQNKBeQsmsss'], ['smssms'], ['mmsmss'], ['yKQNKBeQ'], ['mmmmmsmsssmmsss'], ['msmms'], ['msmyQNyQNKBeQKBeQsmmsmss'], ['msmyQNyQNBKBeQKBeQsmmsmss'], ['mmmsms'], ['mmsms'], ['msmmsms'], ['mmmss'], ['smssm'], ['mss'], ['msmmmss'], ['mmmms'], ['mssmsmyQNKBeQs'], ['mmsmyQNKBeQsmmsss'], ['msmyQNKBeQNs'], ['zWgdk'], ['mmsmsmmssss'], ['mQsmyQNKBeQs'], ['smssmsmyQNKBeQsmssms'], ['mmmmsms'], ['RfuIu'], ['mmssms'], ['RufuIu'], ['mmsmyQNyQNKBeQKBeQsmmmsms'], ['mssmsmysQNKBeQs'], ['mssmsNKBeQs'], ['mmmsmsmss'], ['mmmmsmyQNKBeQsmmsssssms'], ['msmmss'], ['smss'], ['smszWgdksm'], ['smssmms'], ['msmyQNyQNKBeQKBseQsmmsmss'], ['mmsmyQNyQNKBmmmsmseQKBeQsmmmsms'], ['msmmmmsmyQNKBeQNsss'], ['mmmsmss'], ['mmmmmmsmsssmmsss'], ['mmmsmyQNKBeQNsssms'], ['smssmsmymmsmsmmssssQNKBeQsmssms'], ['mmsmyQNKBmeQs'], ['mmmsmyQNyQNKBmmmsmseQKBeQsmmmsmsmsms'], ['mmmmsmsmsmmmmmmsmsssmmsss'], ['mmmssyQNKBeQmss'], ['msmyQNyQKNKBeQKBeQsmmsmss'], ['msmyQNyQKNKBmsmyQNKBeQNseQKBeQsmmsmss'], ['msmyQNyQNKBeQKBseQsmmQsmss'], ['msmyQNKBesQNs'], ['yKQNKBemssmsmysQNKBeQsQ'], ['mmsmyQNKBeQssmmsss'], ['msmmsmmsms'], ['mmyKQNKBeQmssyQNKBeQmss'], ['mmmmsmssmsNKBeQsmsmmms'], ['mmmsmmmsmsssmmsss'], ['smssmmmmmsmsssmmsssm'], ['mmmsmyQNKBeQsmssss'], ['msmyQNyQNBKyBeQKBeQsmmsmss'], ['msmmsmmmsms'], ['mmmsmsmyQNyQNKBeQKBseQsmmsmssms'], ['mmmmmsmyQNKBeQNsssmsmms'], ['mmmmsmsmsmmmmmmsmsssmmmmsmyQNKBeQsmmssssss'], ['mmmmsmyQNKBeQNsssmsmsmmsmmssss'], ['mmmmmmmsmyQNKBeQNsssmsmsmmsmmssssmmsmyQNKBeQNsssmsmms'], ['mssmQsmyQNKBeQs'], ['smmsssmsmymmsmsmmssssQNKBeQsmssms'], ['yKQN'], ['smssmmmmmmmmmsmyQNKBeQNsssmsmsmmsmmssssmmsmyQNKBeQNsssmsmmss'], ['smssmsmyQNKBmmsmyQNKBeQssmmssseQsmssms'], ['Rf'], ['mmRufuIus'], ['smssmBmmsmyQNKBeQssmmssseQsmssms'], ['BmmmsmyQNyQNKBmmmsmseQKBeQsmmmsmsmsmsRfuIu'], ['smsmsmssmsmyQNKBmmsmyssseQsmssms'], ['yKQNKmssmQsmyQNKBeQsBeQ'], ['mssmmmmsmyQNKBeQsmmsssssms'], ['zWgdWk'], ['mssmmms'], ['zWgdW'], ['smmsmyQNKBeQssmmsssmssm'], ['mssmsmysQNKBeQss'], ['mszWgWdWkms'], ['msmssmsmysQNKBeQss'], ['mmsmyQNyQNKBmmmsmseQKBmeQsmmmsms'], ['smszkWgdksm'], ['msmyQNyQNKBeQKBesQsmmsmss'], ['smssmBmmsmyQNKBeQsssmmssseQssmssms']]
result = []
for inp in inputs:
    result.append(all_Characters_Same(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
