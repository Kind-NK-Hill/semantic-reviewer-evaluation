# R1g 来源与逐项改编

来源：ReForm arXiv 2510.24592v3，附录 D.2；原论文 PDF 和 HTML 已保存在 data/raw/sources，哈希见 data/raw/manifest.json。

## 原文

```text
Your role is a Lean4 expert, please help me check consistency between natural language expression and its Lean4 formal statement.
Guidelines for Consistency Check
1. Core Checking Requirements:
- When a critique from a previous autoformalization and consistency check result is provided, you must first analyze its findings and then assess their problems.
- Must carefully compare the Natural Language Statement and the Formal Statement in Lean4 through a rigorous and explicit process.
- Determine if the Lean theorem statement is an exact and faithful formalization of the mathematical problem
- If any result is Incorrect of consistency, briefly list all inconsistencies and reasons leading to the Incorrect determination in comments
Evaluation Stages
1. Math Assertion Analysis
Identify all structurally and semantically relevant components of the mathematical problem, including variables, types, quantifiers, constraints, logic structure, conclusion, and so on. The analysis should be based on the actual content of the text.
2. Lean Statement Analysis
Extract all structurally and semantically relevant components from the Lean statement, including
- Variable domains (e.g., real numbers vs positive real numbers)
- Boundary conditions (especially for 0,1)
- Quantifier scopes
- Prerequisites and assumptions
- Logical implications
3. Comparative Verification
Check for exact correspondence between the math and Lean statements; you may refer to aspects like:
- Semantic alignment, logic structure, and quantifier correctness.
- Preservation of constraints and boundary assumptions.
- Accurate typing and use of variables.
- Syntactic validity and proper Lean usage (free from errors).
- Use of symbols and constructs without semantic drift.
- No missing elements, no unjustified additions, and no automatic corrections or completions.
4. Final Judgement
Based solely on the above analysis, judge whether the Lean statement is a correct and exact formalization of the mathematical problem.
- When a critique from a previous consistency check is provided, you must first analyze its findings and then assess their correctness.
- Result must be strictly ”Correct” or ”Incorrect”
- Use ”Correct” ONLY when 100% mathematical equivalence is confirmed
5. Accuracy Confirmation
If correct: clearly confirm why all elements match.
If incorrect: list all mismatches and explain how each one affects correctness.
Intput Format
The Natural Language Statement:
[A math problem in Natural language]
The Formal Statement in Lean4:
```
lean4
[A Lean 4 theorem statement formalizing the problem]
```
Previous round of autoformalization and sematic validation if provided:
[The existing critique, or an empty string if none exists.]
Output Format
Return exactly one XML object
<
<
comments
>
>
Your brief analysis:
1. Math Assertion Analysis: […]
2. Lean Statement Analysis (Proof Ignored): […]
3. Comparative Verification: […]
4. Conclusion: […]
5. Accuracy Confirmation: […match confirmation or list of discrepancies…]
<
<
/comments
>
>
<
<
consistency
>
>
Correct/Incorrect
<
<
/consistency
>
>
Now! It’s your turn to compare the natural language statement with the formal statement in Lean4:
The Natural Language Statement
{INFORMAL STATEMENT (QUESTION) HERE.}
The Formal Statement in Lean4:
```
lean4
{FORMAL STATEMENT HERE.}
```
Previous autoformalization and consistency Comments:
{HISTORY CRITIC HERE}
Think about the consistent result:
The model’s output here.
```

## 改编记录

### 1. 输出 comments 的要求替换为共同输出要求。

原文：
```text
- If any result is Incorrect of consistency, briefly list all inconsistencies and reasons leading to the Incorrect determination in comments
```

替换：
```text
Return JSON with two fields: "verdict" (one of "faithful", "unfaithful", "uncertain") and "reason" (one sentence stating the main reason).
```

### 2. 二分类输出格式替换为共同三分类 JSON 输出要求。

原文：
```text
- Result must be strictly ”Correct” or ”Incorrect”
```

替换：
```text
Return JSON with two fields: "verdict" (one of "faithful", "unfaithful", "uncertain") and "reason" (one sentence stating the main reason).
```

### 3. 按任务单将正确映射为 faithful，保留确认条件。

原文：
```text
- Use ”Correct” ONLY when 100% mathematical equivalence is confirmed
```

替换：
```text
- Use ”faithful” ONLY when 100% mathematical equivalence is confirmed
```

### 4. 步骤 5 的输出解释要求替换为共同一句理由要求；步骤标题保留。

原文：
```text
If correct: clearly confirm why all elements match.
If incorrect: list all mismatches and explain how each one affects correctness.
```

替换：
```text
Return JSON with two fields: "verdict" (one of "faithful", "unfaithful", "uncertain") and "reason" (one sentence stating the main reason).
```

### 5. 替换原输入占位、前轮历史输入和 XML 输出块；本实验没有前轮历史。

原文：
```text
Intput Format
The Natural Language Statement:
[A math problem in Natural language]
The Formal Statement in Lean4:
```
lean4
[A Lean 4 theorem statement formalizing the problem]
```
Previous round of autoformalization and sematic validation if provided:
[The existing critique, or an empty string if none exists.]
Output Format
Return exactly one XML object
<
<
comments
>
>
Your brief analysis:
1. Math Assertion Analysis: […]
2. Lean Statement Analysis (Proof Ignored): […]
3. Comparative Verification: […]
4. Conclusion: […]
5. Accuracy Confirmation: […match confirmation or list of discrepancies…]
<
<
/comments
>
>
<
<
consistency
>
>
Correct/Incorrect
<
<
/consistency
>
>
Now! It’s your turn to compare the natural language statement with the formal statement in Lean4:
The Natural Language Statement
{INFORMAL STATEMENT (QUESTION) HERE.}
The Formal Statement in Lean4:
```
lean4
{FORMAL STATEMENT HERE.}
```
Previous autoformalization and consistency Comments:
{HISTORY CRITIC HERE}
Think about the consistent result:
The model’s output here.
```

替换：
```text
Return JSON with two fields: "verdict" (one of "faithful", "unfaithful", "uncertain") and "reason" (one sentence stating the main reason).

<problem>
{informal_statement}
</problem>

<lean_header>
{header}
</lean_header>

<lean_statement>
{formal_statement}
</lean_statement>
```
