# 语义审核何时值得信任

**规则提示、重复判断与第二意见的外部校准 · 初稿v0.1 · 2026年11月9日**

完整三批数据已采集并评估：858个唯一输入，19,170次判断。本项目关注审核器什么时候能发现命题不忠实、什么时候会稳定漏错，以及追加审核预算的实际取舍。

- [阅读评估初稿](reports/evaluation-draft.zh-CN.md)：研究目的、设计、主结果、来源差异、重复审核、第二意见及限制。
- [冻结分析结果](results/main_results.json)与[探索性补充](results/supplement.json)：明确区分预定决定与事后解释。
- [15个关键案例](reports/key_cases.md)：保留原题、形式命题和模型回答，尚未经过合格复核者裁决。
- [复现说明](REPRODUCIBILITY.md)：离线重算，无需模型接口；[模拟诊断](protocol/simulation-rates.md)保留失败及方法修订。

预定选择规则给Terra选择R0、给DeepSeek选择R1g。这个决定不等于R0在Terra上漏放最低。R1下两模型仍有59和54道不忠实题三次全部被接受，表明稳定输出不能替代正确性。

```text
python -m pip install -r requirements.txt
python verify_release.py
python reproduce.py
python supplement.py
```

本研究与[原形式化引擎](https://github.com/Kind-NK-Hill/ProbabilityTheoryFormalization)和[既有工作流评估](https://github.com/Kind-NK-Hill/review-history-evaluation)相关，但没有测量原系统的修复或交付收益。数据错误均相对发布标签计算，不能把模型共识当作标签裁决。

作者：邓硕。AI工具参与实现、执行、分析和写作。初稿仍待外部评阅及案例语义复核。
