# reports 目录说明

本目录只保留当前 RQ1 结果需要引用的报告。过期的 smoke、current、recheck、manual/fix 中间报告已经删除，避免后续误读。

## 当前保留报告

### rq1_gpt51_final_auto_regen15_20260612.json

当前最终 RQ1 评估报告。

生成命令：

```bat
conda run -n Npflower python 05_rq1\rq1_main.py evaluate --mode all --output_name gpt51_final --report reports\rq1_gpt51_final_auto_regen15_20260612.json
```

报告内容：

| mode | valid_task_count | missing_file_tasks | no_valid_case_tasks | same_cases / total_cases | accuracy |
|---|---:|---:|---:|---:|---:|
| original | 378 | 0 | 0 | 2269 / 3768 | 60.22% |
| equivalent | 378 | 0 | 0 | 2305 / 3768 | 61.17% |
| non_equivalent | 378 | 0 | 0 | 1515 / 3103 | 48.82% |

说明：

- `valid_task_count` 是进入统计的 task 数。
- `same_cases / total_cases` 是 LLM 输出与本地 oracle 一致的测试用例数。
- `non_equivalent` 的 `total_cases=3103`，是因为本地 compare 会排除变异前后输出相同的 case。
- 当前 non-equivalent 本地执行状态为 `378/378` 成功，且 `Fully same tasks: 0`。

### non_equivalent_auto_regen_15_report.json

第一轮对 15 个问题 non-equivalent task 进行 API 自动重生成的审计报告。

报告内容：

- selected: 15
- fixed: 9
- unfixed: `task_20, task_128, task_129, task_131, task_603, task_787`

### non_equivalent_auto_regen_6_report.json

第二轮对第一轮未通过的 6 个 task 使用增强提示词继续 API 自动重生成的审计报告。

报告内容：

- selected: 6
- fixed: 5
- unfixed: `task_129`

### non_equivalent_auto_regen_task129_report.json

第三轮对最后剩余的 `task_129` 使用更明确提示词进行 API 自动重生成的审计报告。

报告内容：

- selected: 1
- fixed: 1
- unfixed: none

## 报告生成规范

后续每次新增报告时，需要同步更新本文件，至少写清楚：

1. 报告文件名。
2. 生成命令。
3. 报告用途，是最终结果、重生成审计、还是临时 smoke。
4. 核心统计值，例如 `valid_task_count`、`missing_file_tasks`、`no_valid_case_tasks`、`accuracy`。
5. 是否可以作为论文/RQ1 最终结果引用。

如果报告只是临时验证或已经被更新报告覆盖，验证完成后应删除，避免和最终结果混淆。
