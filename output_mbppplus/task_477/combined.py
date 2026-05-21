
def is_lower(string):
    return string.lower()


import os

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'code_result.txt')

inputs = [['InValid'], ['TruE'], ['SenTenCE'], [''], ['True'], ['FALSE'], ['123'], ['StRiNg'], ['LOWER CASE'], ['nUmBeRs 123'], ['    extra spaces    '], ['camelCase'], ['UPPERCASE'], ['LOWER CASOE'], ['LOWER SE'], ['camelCacamelCasese'], ['1123'], ['LOWTrueER CASOE'], ['11123'], ['spaces'], ['LOWER CASCE'], ['LOWTrucamespaceslCacamelCaseseeER CASOE'], ['SE'], ['extra'], ['X'], ['LOWTrucamespaceslCacam11123 CASOE'], ['exxtra'], ['LOWTrucamespaceslCacam11123'], ['Trrue'], ['LOWRER CASOE'], ['LOWEWR CEASE'], ['LOWER CASROE'], ['TUPPERCASErue'], ['Trrrue'], ['LOWER CAROE'], ['LOWER'], ['LOWER CAS ROLOWRERE'], ['LOWER ROLOWRERECAS ROLOWRERE'], ['LOWER LCASCE'], ['CASCE'], ['camelCaese'], ['LOWRER'], ['CAROE'], ['xLOWER CASOexxtraE'], ['camelCasme'], ['eTrrCASOexxtraEue'], ['xLOWER'], ['11eTrrCASOexxtraEue123'], ['eTrrCASOexxtraaEue'], ['C'], ['camelCsme'], ['spnUmBeRsaces'], ['LOWEWR'], ['LOWER ALCASCE'], ['camelCslme'], ['LCASCE'], ['LR CASOE'], ['oa'], ['LOWTrueER'], ['SLOWER SE'], ['eTrrCASOexxtraaEuCASOexxtraEe'], ['LLOWTrueEROWER CASLOWEWR CEASE ROROLOWREREOLOWRERE'], ['TruenUmBeRs'], ['g'], ['CASE'], ['oaa'], ['LOWER ROLOWRERECAS ROLLOWER SEOWRERE'], ['11eTrrCASOexxte123'], ['SSE'], ['FvqXvHKtQ'], ['xLOWERO CASOexxtra'], ['ROROLOWREREOLOWRERE'], ['RACAROE'], ['LOWR SE'], ['cLLOWTrueEROWER CASLOWEWR CEASE ROROLOWREREOLOWREREamelCacamelCasese'], ['eLCASCExtra'], ['sspnUmBeRsaces'], ['LOWER ROLOWRERECAS ROLLOWER SEOWREREoa'], ['Trueg'], ['LOWER ROLOWRERxLOWERO CASOexxtraECAS ROLLOWER SEOWREREoa'], ['cLLOWTrueEROWER'], ['LOWTrueR'], ['11eTrrCASOexxtraExLOWEaROue123'], ['CCAROE'], ['ceamelCasme'], ['SL OWER SE'], ['eLCASCExtraSSE'], ['TUPPERCASErueSE'], ['caeTrrCASexxtraEuemelCase'], ['LOWOTrueER'], ['111323'], ['WLOWEWOR CEASE'], ['CASOexxtraE'], ['SEOWRERE'], ['123LOWTrueER CASOE'], ['cLLOWTrueEROWER CASLOWEWR CEASE ROROLOWREREOLEOWREREamelCacamelCaLOWRER CASOEsese'], ['camTruegelCaese'], ['oeTrrCASOexxtraEueaa'], ['SL OWER oeTrrCASOexxtraEueaaSE'], ['Tre'], ['ROLLOWER'], ['cLLOWTrueEROWERSLOWER SE'], ['CASOexxtra LCASRCE'], ['LOWER cLLOWTrueEROWERSLOWERASCE'], ['LOWER CCE'], ['LsspnUmBeRsacesOWER LCASCE'], ['cLLOWTrueEROWERSLOWERASCE'], ['CASOexxtra LC ASRCE'], ['LROROLOWREREOLEOWREREamelCacamelCaLOWRERER'], ['LCASRCE'], ['spaceROLOWREREs'], ['LR nUmBeRsxLOWERCASOE'], ['12LOWEROROLOWREREOLEOWREREamelCacamelCaLOWRERR CASE3LOWTrueER CASOE']]
result = []
for inp in inputs:
    result.append(is_lower(*inp))
with open('code_result.txt', 'w', encoding='utf-8') as f: f.write(str(result))
