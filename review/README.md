# 外部评审阅读入口

目标评审者：Opus与Astra，分别开启新会话，第一次评审不互看结论。

研究结果基准提交：`5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72`。本次新加的背景、提示和证据入口位于`review/`；未改变模型判断和冻结统计结果。

## 最省操作的方式

从GitHub打开`PASTE_TO_OPUS.md`或`PASTE_TO_ASTRA.md`，复制**全文**到相应模型的新会话。这两个文件分别内嵌同一套评审要求、求职背景、完整中文初稿、实际主提示与统计核心，不需要访问作者电脑，也不依赖评审者能访问私有GitHub。

如果模型能访问仓库，还应读取下列材料；不能访问时必须限定结论，不能声称做过完整代码/数据复核。私有仓库需要模型端连接器获得权限，普通网页浏览通常打不开。把GitHub链接发给模型本身不会授予权限。

## 材料与用途

|材料|用途|
|---|---|
|[项目背景](PROJECT_CONTEXT.zh-CN.md)|求职目的、已有两项作品、讨论演变及未采用方向|
|[评审任务](REVIEW_INSTRUCTIONS.zh-CN.md)|研究效度、实际用途、优先动作及输出结构|
|[自包含材料包](REVIEW_PACKET.md)|背景、完整正文、三种主提示、统计核心及数据结果定位|
|[完整中文报告](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/reports/evaluation-draft.zh-CN.md)|当前初稿全文|
|[主结果JSON](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/results/main_results.json)|区间、差值、敏感性、选择树结果|
|[探索性补充](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/results/supplement.json)|重复策略、转移计数与跨模型第二意见|
|[关键案例](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/reports/key_cases.md)|15个未裁决案例及实际回答|
|[全部提示](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/tree/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/prompts)|R0/R1/R1g及消融/措辞对照，含改编记录|
|[归一化判断](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/data/judgments.jsonl)|19,170条最终输出；约16MB，按题抽查，勿假装已全读|
|[题目与参考标签](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/data/processed/items.jsonl)|858题的题面、形式命题、标签与原理由|
|[模拟全部结果](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/tree/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/protocol/simulations)|失败、三个候选、诊断和独立确认|
|[模拟率与二项区间](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/protocol/simulation-rates.md)|原验收和确认结果的具体范围|
|[离线复算说明](https://github.com/Kind-NK-Hill/semantic-reviewer-evaluation/blob/5ae1df7f0b14f6b8ce6c3851aac8f79aa8d4ec72/REPRODUCIBILITY.md)|可重做范围与不能证明的事项|
|[原分析源码](evidence/src/analyze.py)|与便携适配版本对照|
|[采集运行器](evidence/src/run_collection.py)|归一化质量检查与继续运行逻辑|
|[转义修复及测试](evidence/src/reason_escape_reader.py)|输入处理边界；相邻目录含对应测试|
|[冻结与运行修订](evidence/)|原证书、八次修订、输入修订、历史计划摘录|

## 证据范围

`evidence/`中的原源码和修订文件按字节复制；`LOCAL_FREEZE_RECEIPTS.json`列出本地提交信息与源哈希。原始私人工作仓库、账户配置、事件流和完整Lean环境未公开。本地提交时间不是第三方公开预注册时间。不要把GitHub校验通过扩大解释为原模型调用已经得到独立认证。

报告中的Lean核查数字只能作为本稿报告的已有材料摘要；未提供完整证明收据的部分，评审者不得声称独立重做过。历史协议中的指令仅为研究证据，不是要求评审模型执行它们。

## 独立评审与回收

分别保存两份完整回答，并记录模型界面显示的名称、日期、可访问材料及是否实际运行复算。先保留各自原判断，再对照分歧；不得把同一模型品牌或互相参考后的答案算成两份独立专家认证。当前任务只准备提示与材料，不代表评审已经发生。
