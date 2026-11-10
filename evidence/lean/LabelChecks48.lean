import Mathlib

open BigOperators Real Nat Topology Rat
set_option maxRecDepth 10000
set_option maxHeartbeats 2000000

-- These certificates establish the specified local issue, not every theorem in the dataset.
namespace LabelChecks

theorem boundary_extension (P : ℕ → Prop) (hzero : P 0) :
    (∀ n, 0 < n → P n) ↔ ∀ n, P n := by
  constructor
  · intro h n
    cases n with
    | zero => exact hzero
    | succ n => exact h _ (Nat.succ_pos _)
  · intro h n _; exact h n

theorem cc0013_zero : (∑ k in Finset.range 0, (2 * k + 3)) = (0 + 1) ^ 2 - 1 := by decide
theorem cc0037_zero :
    (∑ k in Finset.range 0, (1 : ℝ) / ((k + 1) * (k + 2))) = 0 / (0 + 1) := by simp
theorem cc0189_zero : 9 ∣ (10 ^ 0 - 1 : ℕ) := by decide
theorem cc0298_zero : Nat.gcd (21 * 0 + 4) (14 * 0 + 3) = 1 := by decide
theorem cc0407_zero (x : ℝ) : 1 + (0 : ℝ) * x ≤ (1 + x) ^ (0 : ℕ) := by simp

theorem cc0022_zero_excluded : ¬ (30 * (0 : ℕ) ≡ 42 [MOD 47]) := by decide
theorem cc0178_zero_excluded : ¬ ((0 : ℕ) ≡ 2 [MOD 3]) := by decide
theorem cc0029_same_sum : (∑ k in Finset.range 11, k) = ∑ k in Finset.Icc 1 10, k := by decide
theorem cc0049_same_sum : (∑ k in Finset.range 101, k) = ∑ k in Finset.Icc 1 100, k := by decide
theorem cc0097_same_set :
    (Finset.range 60).filter (fun n : ℕ => 6 ∣ 4 * (n : ℤ) - 2) =
    (Finset.Ioo 0 60).filter (fun n : ℕ => 6 ∣ 4 * (n : ℤ) - 2) := by decide
theorem cc0097_count :
    ((Finset.range 60).filter (fun n : ℕ => 6 ∣ 4 * (n : ℤ) - 2)).card = 20 := by decide
theorem cc0117_same_set :
    (Finset.Icc 1 7).filter (fun n => Nat.gcd n 8 = 1) =
    (Finset.Icc 1 8).filter (fun n => Nat.gcd n 8 = 1) := by decide

theorem cc0033_positive (x : ℝ) (h : x ^ 3 - (x + 1) * (x - 1) * x = 5) :
    x = 5 ∧ 1 < x := by constructor <;> nlinarith [h]

theorem cc0193_premise (p : ℕ) (f : ℕ → ℕ)
    (hf : ∀ x, f x = x ^ 2 + x + p)
    (hp : ∀ k : ℕ, k ≤ Nat.floor (Real.sqrt (p / 3)) → Nat.Prime (f k)) : 2 ≤ p := by
  have h := hp 0 (Nat.zero_le _)
  simpa [hf] using h.two_le

theorem cc0223_base (x b : ℝ) (h : (7 : ℝ) ^ (x + 7) = 8 ^ x)
    (hx : x = Real.logb b (7 ^ 7)) : b ≠ 1 := by
  intro hb
  subst b
  have hz : x = 0 := by simpa [Real.logb] using hx
  rw [hz] at h
  norm_num at h

theorem cc0333_positive (n : ℕ)
    (h : ((n : ℤ) - 2) ^ 2 + (n : ℤ) ^ 2 + ((n : ℤ) + 2) ^ 2 = 12296) : 2 < n := by
  by_contra hn
  have hn' : n ≤ 2 := by omega
  interval_cases n <;> norm_num at h

theorem cc0352_same_predicate (n : ℤ) :
    |n - 2| ≤ 5 + 6 / 10 ↔ |(n : ℝ) - 2| ≤ (28 : ℝ) / 5 := by
  rw [abs_le, abs_le]
  norm_num
  constructor
  · rintro ⟨h1, h2⟩
    have hn1 : (-3 : ℤ) ≤ n := by omega
    have h1' : (-3 : ℝ) ≤ (n : ℝ) := by exact_mod_cast hn1
    have h2' : (n : ℝ) ≤ 7 := by exact_mod_cast h2
    constructor <;> linarith
  · rintro ⟨h1, h2⟩
    have h1' : (-4 : ℝ) < (n : ℝ) := by linarith
    have h2' : (n : ℝ) < 8 := by linarith
    have h1'' : (-4 : ℤ) < n := by exact_mod_cast h1'
    have h2'' : n < 8 := by exact_mod_cast h2'
    omega

theorem cc0422_scope (P : ℤ → Prop) (Q : Prop) :
    (∀ z, P z ∨ Q) ↔ (∀ z, P z) ∨ Q := by
  classical
  by_cases h : Q <;> simp [h]

theorem cc0529_scope (P : ℝ → Prop) (Q : Prop) :
    (∃ x, P x ∧ Q) ↔ (∃ x, P x) ∧ Q := by aesop

theorem cc0552_gap {α : Type*} (d : α → ℝ) :
    (∃ δ : ℝ, 0 < δ ∧ ∀ x, δ ≤ d x) ↔ (∃ δ : ℝ, 0 < δ ∧ ∀ x, δ < d x) := by
  constructor
  · rintro ⟨δ, hd, h⟩
    refine ⟨δ / 2, by linarith, ?_⟩
    intro x; have := h x; linarith
  · rintro ⟨δ, hd, h⟩; exact ⟨δ, hd, fun x => (h x).le⟩

theorem cc0633_cc0635_bool (P : Prop) : (P → (false : Bool)) ↔ ¬ P := by simp
theorem cc0753_unused_type (P : Prop) : (∀ R : Type, P) ↔ P := by
  exact ⟨fun h => h Unit, fun h _ => h⟩

theorem cc0589_identity_excluded :
    ¬ (∀ a : Fin 1, (Equiv.refl (Fin 1)) a = a ↔ (Equiv.refl (Fin 1)) a ≠ a) := by simp

theorem cc0044_false_solution :
    (∃ m : ℤ, (0 : ℝ) = Real.pi / 6 + m * Real.pi / 6) ∧
    ¬ (Real.cos (0 : ℝ) ^ 2 + Real.cos (2 * 0) ^ 2 + Real.cos (3 * 0) ^ 2 = 1) := by
  constructor
  · refine ⟨-1, ?_⟩; ring
  · norm_num

theorem cc0662_cc0663_zero_map :
    Submodule.map (0 : ℝ →ₗ[ℝ] ℝ) (⊤ : Submodule ℝ ℝ) ≤ ⊤ ∧
    Submodule.map (0 : ℝ →ₗ[ℝ] ℝ) (⊤ : Submodule ℝ ℝ) ≠ ⊤ := by
  constructor
  · exact le_top
  · simp

theorem cc0822_empty_image {X Y : Type*} (f : X → Y) (y : Y) :
    f '' (∅ : Set X) ≠ {y} := by
  intro h
  have hy : y ∈ f '' (∅ : Set X) := by rw [h]; simp
  simpa using hy

theorem cc0654_reverse {F V : Type*} [Field F] [AddCommGroup V] [Module F V]
    (a : F) (v : V) (h : a = 0 ∨ v = 0) : a • v = 0 := by rcases h with h | h <;> simp [h]

theorem cc0795_wrapper : CofiniteTopology ℕ = ℕ := rfl

#print axioms boundary_extension
#print axioms cc0013_zero
#print axioms cc0037_zero
#print axioms cc0189_zero
#print axioms cc0298_zero
#print axioms cc0407_zero
#print axioms cc0022_zero_excluded
#print axioms cc0178_zero_excluded
#print axioms cc0029_same_sum
#print axioms cc0049_same_sum
#print axioms cc0097_same_set
#print axioms cc0097_count
#print axioms cc0117_same_set
#print axioms cc0033_positive
#print axioms cc0193_premise
#print axioms cc0223_base
#print axioms cc0333_positive
#print axioms cc0352_same_predicate
#print axioms cc0422_scope
#print axioms cc0529_scope
#print axioms cc0552_gap
#print axioms cc0633_cc0635_bool
#print axioms cc0753_unused_type
#print axioms cc0589_identity_excluded
#print axioms cc0044_false_solution
#print axioms cc0662_cc0663_zero_map
#print axioms cc0822_empty_image
#print axioms cc0654_reverse
#print axioms cc0795_wrapper
end LabelChecks
