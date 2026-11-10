import Mathlib
import Aesop

set_option maxHeartbeats 0
open BigOperators Real Nat Topology Rat

-- Preserve the benchmark's declaration and legacy `in` syntax. The placeholder
-- is ONLY for type inspection, not a proof; none of the proofs below use it.
theorem induction_prod1p1onk3le3m1onn (n : ℕ) (h₀ : 0 < n) :
    (∏ k in Finset.Icc 1 n, 1 + (1 : ℝ) / k ^ 3) ≤ (3 : ℝ) - 1 / ↑n := by
  sorry

noncomputable def cc0335_expression (n : ℕ) (k : ℝ) : ℝ :=
    (∏ k in Finset.Icc 1 n, 1 + (1 : ℝ) / k ^ 3)

theorem cc0335_scope (n : ℕ) (k : ℝ) :
    cc0335_expression n k = (∏ j in Finset.Icc 1 n, (1 : ℝ)) + (1 : ℝ) / k ^ 3 := rfl

-- A closed expression: the original cc_0336 proposition is false.
theorem cc0336_original_false : ¬ ((∏ k in Finset.range 6, 2 * k + 1) % 10 = 5) := by decide

-- The same expression with parentheses around the intended product body.
theorem cc0336_parenthesized_true : (∏ k in Finset.range 6, (2 * k + 1)) % 10 = 5 := by decide

set_option pp.notation false in
#print cc0335_expression
#check @induction_prod1p1onk3le3m1onn
#print axioms cc0335_scope
#print axioms cc0336_original_false
#print axioms cc0336_parenthesized_true
