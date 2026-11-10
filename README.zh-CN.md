# 语义审核何时值得信任

**规则提示、重复判断与第二意见的外部校准 · v0.4 · 2026年11月10日**

完整三批数据已采集并评估：858个唯一输入，19,170次判断。本项目关注审核器什么时候能发现命题不忠实、什么时候会稳定漏错，以及追加审核预算的实际取舍。

- [阅读评估报告](reports/evaluation-draft.zh-CN.md)：研究目的、主结果、分组差异、重复审核、第二意见及具体解析案例。
- [冻结分析结果](results/main_results.json)与[探索性补充](results/supplement.json)：明确区分预定决定与事后解释。
- [15个关键案例](reports/key_cases.md)：保留原题、形式命题和模型回答，保留初始记录，后续技术判断见复核附录。
- [74题技术复核](reports/technical-label-review.zh-CN.md)：逐题判断、证明与反例、修正建议及标签敏感性结果。
- [11月10日新增证据](reports/review-followup.md)：分组结果、74题复核队列与[可运行的Lean检查](evidence/lean/README.md)。
- [复现说明](REPRODUCIBILITY.md)：离线重算，无需模型接口；[模拟诊断](protocol/simulation-rates.md)保留失败及方法修订。

预定比较先检验R1显著改善，再检验其他提示的非劣；最终给Terra选择R0、给DeepSeek选择R1g。它不是全局部署推荐。R1g来自发布本基准的ReForm工作，不能将其表现推广为独立通用审核方法的胜出。R1下两模型仍有59和54道发布标签为不忠实的题三次全部被接受。

修订稿补入Terra R1g与R0的直接比较、换提示/重复/第二意见的同题取舍及准确匹配调用的已记录费用，并区分原始格式阻断与修复后语义指标。冻结主结果不变；新增比较均标为探索性。

v0.4进一步解释总体指标：Terra加六条规则后，缺少前提类漏放上升7.78个百分点，其余题下降1.90个百分点；两者方向相反。26道题在全部25次判断中一致违背不忠实标签；复核后18题可接受、5题仍不忠实、3题属于约定差异。两个Lean案例则把疑问推进到机器证据：`cc_0335`中的k落在乘积之外；`cc_0336`原闭式为假，仅补上主体括号后为真。

```text
python -m pip install -r requirements.txt
python verify_release.py
python reproduce.py
python supplement.py
python post_review.py --check
python label_sensitivity.py --check
```

本研究与[原形式化引擎](https://github.com/Kind-NK-Hill/ProbabilityTheoryFormalization)和[既有工作流评估](https://github.com/Kind-NK-Hill/review-history-evaluation)相关，但没有测量原系统的修复或交付收益。原主结果以发布标签计算，另列复核标签情景；模型共识本身不能裁决标签。

作者：邓硕。AI工具参与实现、执行、分析和写作。已根据外部模型反馈补充复算与机器证据；74道定向分歧题已完成有证据的技术复核，未把它视为独立人工金标准。

复核情景更改48个标签后，绝对错误率下降，但既有规则仍选择Terra R0与DeepSeek R1g。原标签结果与复核情景并列，逐项依据、不同标准下的解释和未更改的输入均可查看。
