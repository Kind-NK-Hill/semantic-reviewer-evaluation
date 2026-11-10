import Mathlib
open Fintype Complex Polynomial LinearMap FiniteDimensional Module Module.End Filter Real Function
open scoped BigOperators Topology
#check (fun n => Real.sqrt (n + 1) - Real.sqrt n)
#check Module.finrank
example {V : Type*} [AddCommGroup V] [Module ℝ V] [FiniteDimensional ℝ V]
    (U : Submodule ℝ V) : Prop := Even (Module.finrank U)
