# 三个标签问题的复核结论

三个问题现已给出技术结论：cc_0037、cc_0097 可接受，cc_0335 不忠实。逐题标准、证据及完整74题复核见[技术复核记录](technical-label-review.zh-CN.md)。原始标签保存在数据文件中；新的标签情景已单独重算。

## cc_0037：边界扩展与忠实性标准

状态：技术复核可接受；发布标签：不忠实。

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

复核结论：接受。已直接验证 n=0 时两端为0，并证明给定 P(0) 后，∀n>0,P(n) 与 ∀n:ℕ,P(n) 等价。这里依靠可核查的边界等价，而不是一般接受更强真命题。证据：`cc0037_zero`、`boundary_extension`。

## cc_0097：筛选条件是否已排除零

状态：技术复核可接受；发布标签：不忠实。

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

复核结论：接受。Lean 的 `cc0097_same_set` 证明两种范围筛选后的集合完全相同，`cc0097_count` 证明基数为20。发布理由忽略了筛选条件，不能成立。

## cc_0335：量词作用域与发布理由

状态：技术复核不忠实，维持发布标签。

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

11月10日核查：原先“形式命题看起来在乘积内部使用绑定的k”的判断不可靠，应撤回。Mathlib将求积主体的解析优先级定为67，主体在低于该优先级的加法之前结束。Lean 4.8.0下保留原`in`写法，可用`rfl`证明表达式展开为对常数1求积，再加`1 / k ^ 3`；原头部的类型检查还显示额外的隐含参数`{k : ℝ}`。发布理由所指的作用域问题成立。

代码、固定版本、命令及输出见[Lean解析证据](../evidence/lean/README.md)。类型检查中的占位证明仅用于展示头部；作用域等式的独立证明不依赖它。早先Lean 4.31探针曾将`in`改写为`∈`，本次4.8检查消除了这一语法改写要求，但不声称复原上游所有执行环境。

复核结论：不忠实。形式命题将逐项乘积替换为常数乘积后的一次加法，并多出一个原题没有的自由参数，改变了比较对象。修复是给整个乘积主体加括号。
