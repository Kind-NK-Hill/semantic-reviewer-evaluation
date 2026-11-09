# 三个具体标签争议：待合格复核者判断

本页在外部模型评审后定向整理，不属于随机标签审计，也不改变原15例的冻结选例或发布标签。三个条目均未裁决，不能据此估计整套数据的标签错误率。

建议先依据书面忠实性标准独立查看题目和命题，再查看现有理由；不明确的标准要先记录分歧。需要数学及Lean语义能力，不能用两个模型投票代替复核。

## cc_0037：边界扩展与忠实性标准

状态：未决；发布标签：不忠实；不据本页重计模型分数。

原题：
Show that for positive integer $n$, $\sum_{k=0}^{n-1} \frac{1}{(k+1)(k+2)} = \frac{n}{n+1}$.

形式命题（含原头部，省略证明）：
```lean
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

theorem induction_sum_1oktkp1 (n : ℕ) :
  (∑ k in Finset.range n, (1 : ℝ) / ((k + 1) * (k + 2))) = n / (n + 1) := by

```

发布理由：["missing hypothesis that n is positive"]

要回答的问题：原题限制n为正，形式命题量化所有自然数。应先明确验收准则是否接受覆盖原题且多含n=0的更强真命题，再判断此例；不能只因扩展点也成立就直接改标签。

复核结果留空：采用的判定标准；逐项证据；结论与置信程度；复核者及日期；是否需要第二人复核。

## cc_0097：筛选条件是否已排除零

状态：未决；发布标签：不忠实；不据本页重计模型分数。

原题：
How many integers $n$ satisfy $0<n<60$ and $4n\equiv 2\pmod 6?$ Show that it is 20.

形式命题（含原头部，省略证明）：
```lean
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

theorem mathd_numbertheory_211 :
  Finset.card (Finset.filter (fun n => 6 ∣ 4 * ↑n - (2 : ℤ)) (Finset.range 60)) = 20 := by

```

发布理由：["use `Finset.Ioo 0 60` instead of `Finset.range 60` because n is positive"]

要回答的问题：Finset.range 60包含零，但其后的整数整除条件在零处为6∣−2，并不成立。请核对整个筛选集合与0<n<60且4n≡2 mod6是否相同，以及“缺少正整数限制”的发布理由是否成立。此处只是定向疑点，不代表已完成Lean语义裁决。

复核结果留空：采用的判定标准；逐项证据；结论与置信程度；复核者及日期；是否需要第二人复核。

## cc_0335：量词作用域与发布理由

状态：未决；发布标签：不忠实；不据本页重计模型分数。

原题：
Show that for any positive integer $n$, we have $\prod_{k=1}^n (1 + 1/k^3) \leq 3 - 1/n$.

形式命题（含原头部，省略证明）：
```lean
import Mathlib
import Aesop

set_option maxHeartbeats 0

open BigOperators Real Nat Topology Rat

theorem induction_prod1p1onk3le3m1onn (n : ℕ) (h₀ : 0 < n) :
    (∏ k in Finset.Icc 1 n, 1 + (1 : ℝ) / k ^ 3) ≤ (3 : ℝ) - 1 / ↑n := by

```

发布理由：["k is outside the scope of production"]

要回答的问题：发布理由称k在乘积作用域之外；形式命题看起来在乘积内部使用绑定的k。请逐项核对绑定范围、类型、幂与原题，判断是否确有语义偏差，避免仅按自然语言理由的措辞裁决。

复核结果留空：采用的判定标准；逐项证据；结论与置信程度；复核者及日期；是否需要第二人复核。

