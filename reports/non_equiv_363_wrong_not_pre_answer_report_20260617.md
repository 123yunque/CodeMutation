# Non-Equivalent RQ1 Error Analysis: Wrong Answers Not Equal To Pre-Mutation Answers

## Scope

This report analyzes cases where the model answered the original program correctly, the non-equivalent mutation changed the expected output, the model answered the mutated program incorrectly, and the wrong mutated-program answer was not the original program answer.

## Data Sources

- Task root: `output_mbppplus_new`
- Original LLM outputs: `sample_output_LLMs_original_code\gpt51_final`
- Non-equivalent LLM outputs: `sample_output_LLMs_non_equivalent_code\gpt51_final`
- JSON details: `reports\non_equiv_363_wrong_not_pre_answer_20260617.json`

## Summary

- Valid changed non-equivalent cases: `3103`
- Original-correct cases: `1770`
- Original-correct but mutated-wrong cases: `524`
- Wrong answer equals pre-mutation answer: `161`
- Wrong answer is not pre-mutation answer: `363`

## Key Rates

- Mutation-induced wrong rate among original-correct cases: `524 / 1770 = 29.60%`
- Reused pre-mutation answer among mutation-induced wrong cases: `161 / 524 = 30.73%`
- Other wrong answers among mutation-induced wrong cases: `363 / 524 = 69.27%`
- Other wrong answers among original-correct cases: `363 / 1770 = 20.51%`

## Answer Type Distribution

| Answer type | Count | Share |
|---|---:|---:|
| `int` | 162 | 44.63% |
| `list` | 97 | 26.72% |
| `tuple` | 30 | 8.26% |
| `float` | 30 | 8.26% |
| `text` | 25 | 6.89% |
| `other` | 7 | 1.93% |
| `dict` | 6 | 1.65% |
| `None` | 2 | 0.55% |
| `set` | 2 | 0.55% |
| `empty` | 1 | 0.28% |
| `bool` | 1 | 0.28% |

## Error Category Distribution

| Error category | Count | Share |
|---|---:|---:|
| `numeric_miscalculation` | 183 | 50.41% |
| `container_structure_or_order` | 135 | 37.19% |
| `string_transformation_error` | 25 | 6.89% |
| `float_precision` | 9 | 2.48% |
| `other` | 7 | 1.93% |
| `boundary_or_special_value` | 4 | 1.10% |

## Top Repeated Wrong Answers

| Wrong answer | Count |
|---|---:|
| `2` | 11 |
| `99999999999999999999` | 10 |
| `1` | 9 |
| `0` | 9 |
| `8` | 5 |
| `7` | 5 |
| `4` | 5 |
| `9` | 5 |
| `5` | 4 |
| `16` | 4 |
| `3` | 3 |
| `14` | 3 |
| `36` | 2 |
| `28` | 2 |
| `12` | 2 |
| `[False, False, None, None, True, True, 'KFgDNCb', 'KFgDNCb', True, True, None, None, -3.196651036104, -3.196651036104...` | 2 |
| `None` | 2 |
| `1.3499999999999996` | 2 |
| `11` | 2 |
| `[1]` | 2 |

## Tasks With Most Cases

| Task | Count |
|---|---:|
| `task_612` | 10 |
| `task_763` | 10 |
| `task_606` | 9 |
| `task_778` | 9 |
| `task_583` | 8 |
| `task_586` | 8 |
| `task_167` | 7 |
| `task_390` | 7 |
| `task_432` | 7 |
| `task_615` | 7 |
| `task_797` | 7 |
| `task_244` | 6 |
| `task_389` | 6 |
| `task_791` | 6 |
| `task_162` | 5 |
| `task_116` | 4 |
| `task_119` | 4 |
| `task_120` | 4 |
| `task_139` | 4 |
| `task_224` | 4 |

## Interpretation

- These cases are not simple persistence of the original output. The model changed its answer, but computed a third result that matches neither the original behavior nor the mutated behavior.
- Numeric errors are the largest group, suggesting incorrect execution of modified arithmetic, boundary conditions, loop updates, or index changes.
- Container errors are also common, covering list, tuple, set, and dict outputs where the model often gets part of the structure right but misses ordering, filtering, nesting, or element selection.
- String transformation errors show partial adaptation: the model often applies a plausible transformation but not exactly the mutated program semantics.
- Float errors should be interpreted carefully because the strict evaluator uses exact string matching.

## Example Cases

| Task | Case | Input | Pre expected | Mutated expected | Mutated LLM answer | Type | Category |
|---|---:|---|---|---|---|---|---|
| `task_101` | 3 | `[[7, 100, 100, 98, 20, 97, 96, 100, 100], 6]` | `97` | `98` | `20` | `int` | `numeric_miscalculation` |
| `task_102` | 5 | `['programming_language']` | `ProgrammingLanguage` | `Programming_language` | `Programming_Language` | `text` | `string_transformation_error` |
| `task_103` | 4 | `[5, 1]` | `26` | `52` | `354` | `int` | `numeric_miscalculation` |
| `task_103` | 10 | `[5, 2]` | `66` | `132` | `508` | `int` | `numeric_miscalculation` |
| `task_104` | 10 | `[[['apple', 'green'], ['apple', 'green'], ['apple', 'green'], ['black', 'white', 'black...` | `[['apple', 'green'], ['apple', 'green'], ['apple', 'green'], ['black', 'black', 'white'...` | `[['green', 'apple'], ['green', 'apple'], ['green', 'apple'], ['white', 'white', 'black'...` | `[['green', 'apple'], ['green', 'apple'], ['green', 'apple'], ['white', 'white', 'black'...` | `list` | `container_structure_or_order` |
| `task_106` | 1 | `[[[[1, 2], [3, 4]], [[5, 6], [7, 8]], [[5, 6], [7, 8]]], ([[9, 10], [11, 12]], [[13, 14...` | `([[9, 10], [11, 12]], [[13, 14], [15, 16]], [[1, 2], [3, 4]], [[5, 6], [7, 8]], [[5, 6]...` | `([[1, 2], [3, 4]], [[5, 6], [7, 8]], [[5, 6], [7, 8]], [[9, 10], [11, 12]], [[13, 14], ...` | `([[[1, 2], [3, 4]], [[5, 6], [7, 8]], [[5, 6], [7, 8]]], ([[9, 10], [11, 12]], [[13, 14...` | `tuple` | `container_structure_or_order` |
| `task_116` | 1 | `[(123456789123456789, 9999999999999999999, 123456789123456789)]` | `1234567891234567899999999999999999999123456789123456789` | `1234567891234567899999999999999999999123456789123456790` | `12345678912345678910000000000000000000` | `int` | `numeric_miscalculation` |
| `task_116` | 4 | `[(9876543210987654321, 987, 321, 321)]` | `9876543210987654321987321321` | `9876543210987654321987321322` | `98765432109876543210987321321` | `int` | `numeric_miscalculation` |
| `task_116` | 6 | `[(123456789123456789, 987654321987654321, 123456789123456789, 9999999999999999999)]` | `1234567891234567899876543219876543211234567891234567899999999999999999999` | `1234567891234567899876543219876543211234567891234567900000000000000000000` | `12345678912345678998765432198765432112345678912345678999999999999999999910` | `int` | `numeric_miscalculation` |
| `task_116` | 10 | `[(123, 456, 789)]` | `123456789` | `123456790` | `1234567891` | `int` | `numeric_miscalculation` |
| `task_119` | 1 | `[[1, 3, 4, 7]]` | `1` | `0` | `5` | `int` | `numeric_miscalculation` |
| `task_119` | 4 | `[[0, 2, 2, 2]]` | `2` | `3` | `1` | `int` | `numeric_miscalculation` |
| `task_119` | 8 | `[[0, 1, 4, 4, 5, 6]]` | `2` | `3` | `5` | `int` | `numeric_miscalculation` |
| `task_119` | 10 | `[[4, 4, 6]]` | `6` | `7` | `3` | `int` | `numeric_miscalculation` |
| `task_120` | 2 | `[[(-10, 0), (0, 5)]]` | `0` | `10` | `5` | `int` | `numeric_miscalculation` |
| `task_120` | 6 | `[[(0.1, 0.1), (0.5, -0.5), (0.2, 0.2)]]` | `0.25` | `0.4` | `0.30000000000000004` | `float` | `numeric_miscalculation` |
| `task_120` | 7 | `[[(0, 10), (-100, 100), (0, 10), (0, 10)]]` | `10000` | `10` | `200` | `int` | `numeric_miscalculation` |
| `task_120` | 8 | `[[(-10, 20), (100000, -2), (-10, 20)]]` | `200000` | `99998` | `99992` | `int` | `numeric_miscalculation` |
| `task_124` | 4 | `(1e-100, 1e-100j)` | `0.7853981633974483` | `-0.7853981633974483` | `-2.356194490192345` | `float` | `numeric_miscalculation` |
| `task_127` | 3 | `[-999999999999999999, 999999999999999998]` | `-999999999999999997000000000000000002` | `-999999999999999998000000000000000001` | `-999999999999999999` | `int` | `numeric_miscalculation` |
| `task_127` | 6 | `[-999999999999999998, -999999999999999998]` | `999999999999999996000000000000000004` | `999999999999999995000000000000000006` | `0` | `int` | `numeric_miscalculation` |
| `task_128` | 1 | `[3, 'python is a programming language']` | `['python', 'programming', 'language']` | `['python', 'programming']` | `['python']` | `list` | `container_structure_or_order` |
| `task_128` | 6 | `[0, 'thisisaverylongword testing wordlengths']` | `['thisisaverylongword', 'testing', 'wordlengths']` | `[]` | `['thisisaverylongword']` | `list` | `container_structure_or_order` |
| `task_128` | 7 | `[0, 'thisisaverylongwordnopqrsw teseting wordlengths']` | `['thisisaverylongwordnopqrsw', 'teseting', 'wordlengths']` | `[]` | `['thisisaverylongwordnopqrsw']` | `list` | `container_structure_or_order` |
| `task_130` | 4 | `[[1, 2, 3, 4, 6, 7, 8, 8, 9, 10, 11, 11, 13, 3, 15]]` | `3` | `1` | `8` | `int` | `numeric_miscalculation` |
| `task_132` | 2 | `[('SkpnaC', 'Z', 'a', 'qHPQEqCm', 'PyvCTG', 'aFELUEp', 'aZZ', 'IWSYg', 'Z')]` | `SkpnaCZaqHPQEqCmPyvCTGaFELUEpaZZIWSYgZ` | `ZIWSYgaZZaFELUEpPyvCTGqHPQEqCmaZSkpnaC` | `ZZIWSYgaZZFELUEFaGTCvyPmqEQPHqaZCnapkS` | `text` | `string_transformation_error` |
| `task_132` | 8 | `[('aa', 'VekfW', 'a')]` | `aaVekfWa` | `aVekfWaa` | `aWfkevVaa` | `text` | `string_transformation_error` |
| `task_132` | 9 | `[('Z', 'aaZ', 'IWSYga', 'a', 'ZvCAMhN', 'PBEOJoMiYa', 'a', 'a', 'a')]` | `ZaaZIWSYgaaZvCAMhNPBEOJoMiYaaaa` | `aaaPBEOJoMiYaZvCAMhNaIWSYgaaaZZ` | `aaaaqMiYoJEOBPNhMACvZaaygSWSIaZaaZ` | `text` | `string_transformation_error` |
| `task_133` | 10 | `[[3, 2, 1, -7, 2.5, 4, -6, 1, 1]]` | `-13` | `-14` | `-15` | `int` | `numeric_miscalculation` |
| `task_135` | 6 | `[100]` | `19900` | `299` | `199` | `int` | `numeric_miscalculation` |
| `task_139` | 3 | `[85]` | `534.0707511102648` | `0.07391982714328925` | `0.07382304768722034` | `float` | `numeric_miscalculation` |
| `task_139` | 4 | `[98]` | `615.7521601035994` | `0.0641141357875468` | `0.06407968412375855` | `float` | `numeric_miscalculation` |
| `task_139` | 8 | `[55]` | `345.57519189487726` | `0.11423973285781065` | `0.11423973285751097` | `float` | `float_precision` |
| `task_139` | 10 | `[88]` | `552.9203070318035` | `0.07139983303613166` | `0.07139983303613184` | `float` | `float_precision` |
| `task_145` | 1 | `[[-5, 4, 0, -6, -3, -1, -1]]` | `10` | `-2` | `-1` | `int` | `numeric_miscalculation` |
| `task_145` | 3 | `[[8, -4, 2, -5, 4, 1, 11, 8, -7, 1]]` | `18` | `4` | `7` | `int` | `numeric_miscalculation` |
| `task_161` | 4 | `[[2, 4, 6, 8, 'abc', 6], ['abc', 'axyz', 4.5, 'applegrape']]` | `[2, 4, 6, 8, 6]` | `['abc']` | `[]` | `list` | `container_structure_or_order` |
| `task_161` | 7 | `[[[4, 10, 4], [3, 4], [7, 8], [4, 10, 4]], [[4, 10, 4], [3, 4], [7, 8], [4, 10, 4]]]` | `[]` | `[[4, 10, 4], [3, 4], [7, 8], [4, 10, 4]]` | `[[[4, 10, 4], [3, 4], [7, 8], [4, 10, 4]]]` | `list` | `container_structure_or_order` |
| `task_162` | 3 | `[18]` | `90` | `88` | `16` | `int` | `numeric_miscalculation` |
| `task_162` | 5 | `[20]` | `110` | `108` | `36` | `int` | `numeric_miscalculation` |
| `task_162` | 6 | `[19]` | `100` | `96` | `28` | `int` | `numeric_miscalculation` |
| `task_162` | 7 | `[4]` | `6` | `4` | `0` | `int` | `numeric_miscalculation` |
| `task_162` | 8 | `[6]` | `12` | `10` | `4` | `int` | `numeric_miscalculation` |
| `task_166` | 1 | `[[-3, -2, 80, -200, 3]]` | `4` | `6` | `2` | `int` | `numeric_miscalculation` |
| `task_167` | 1 | `[38]` | `64` | `4096` | `128` | `int` | `numeric_miscalculation` |
| `task_167` | 2 | `[987654321098]` | `1099511627776` | `1208925819614629174706176` | `2199023255552` | `int` | `numeric_miscalculation` |
| `task_167` | 3 | `[1234567890122]` | `2199023255552` | `4835703278458516698824704` | `8796093022208` | `int` | `numeric_miscalculation` |
| `task_167` | 4 | `[17]` | `32` | `1024` | `64` | `int` | `numeric_miscalculation` |
| `task_167` | 6 | `[6]` | `8` | `64` | `16` | `int` | `numeric_miscalculation` |
| `task_167` | 7 | `[1000000]` | `1048576` | `1099511627776` | `4194304` | `int` | `numeric_miscalculation` |

## Reproducibility Notes

- The JSON file contains all 363 cases with task id, case index, input, original expected answer, mutated expected answer, original LLM answer, mutated LLM answer, answer type, and error category.
- The counts are based on current files in `gpt51_final`; rerunning LLM generation may change the result set.
- The analysis excludes non-equivalent cases where the mutation did not change local output for that input.
