# Lean notation evidence

This probe checks two concrete issues raised during the November 10 review.
It uses the study's existing Lean 4.8.0 environment and Mathlib revision
`b5eba595428809e96f3ed113bc7ba776c5f801ac`, preserving the dataset's `in` syntax.
This identifies the tested environment, not every environment used upstream.

- **cc_0335:** `cc0335_scope` proves by `rfl` that the product body is the
  constant 1 and that the following addition is outside it. Inspecting the
  original declaration shows a separate implicit real-valued `k`.
- **cc_0336:** `cc0336_original_false` proves by `decide` that the original
  closed proposition is false. `cc0336_parenthesized_true` proves that the
  expression with parentheses around `2 * k + 1` has the stated remainder 5.
  Both are direct formal checks, not model-generated verdicts.

The original cc_0335 declaration has a `sorry` solely to inspect its type.
It is not a proof of the benchmark theorem. The three independent checks print
their axiom dependencies: none uses this declaration or `sorryAx`. The expected
placeholder and unused-variable warnings are retained in the output.

## Reproduce

In a Mathlib project pinned to Lean 4.8.0 and the revision above, run:

```sh
lake env lean /path/to/semantic-reviewer-evaluation/evidence/lean/ScopeCheck48.lean
```

For a fresh project, use `leanprover/lean4:v4.8.0` in `lean-toolchain` and a
Mathlib dependency at the revision above; its dependencies/cache must be
installed before running the command. The Python-only CI does not install Lean.

[Source](ScopeCheck48.lean), [output](ScopeCheck48.stdout.txt), and
[environment record](environment.json) are included. The command exited 0.
The recorded output replaces the local workspace path with `<workspace>`;
the mathematical output and warnings are otherwise retained.

An earlier Lean 4.31 probe rewrote `in` to `∈`; the 4.8 probe removes that
rewrite requirement. These two cases do not adjudicate all remaining cases,
and the parenthesized expression was not submitted in a new model experiment.
