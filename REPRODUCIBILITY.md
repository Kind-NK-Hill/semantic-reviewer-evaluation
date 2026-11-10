# Reproduction scope

The package reproduces analysis from completed judgments. It does not make new
model calls, recover hidden provider state, or independently judge semantic
labels. The Python workflow does not rerun Lean; a separate two-case Lean
probe is supplied below. Python 3.12 and pinned dependencies are recorded in
`requirements.txt`.

1. `python verify_release.py` verifies the allowlisted publication files.
2. `python reproduce.py` checks all 19,170 unique records, validates 114 repairs,
   recomputes the frozen model-level statistics and checks every returned field.
3. `python supplement.py` computes the explicitly exploratory repeat-policy,
   matched-transition and cross-model diagnostics.
4. `python post_review.py --check` recomputes the November 10 exploratory C1
   split, unanimous disagreements, 74-item priority queue, and notation-case
   counts, comparing them with `results/post_review.json`.

Outputs go to `recomputed/`, preserving saved results. `results/main_results.json`
contains the original frozen analyzer output. The function bodies in
`src/analysis_core.py` were extracted unchanged from the local frozen analyzer;
`src/adapter.py` supplies portable file readers and the saved attempt ledger.
`src/statistics_core.py` is byte-identical to the frozen statistical source.
Original source hashes are in `protocol/provenance.json`.

`data/judgments.jsonl` contains final model outputs, normalized verdicts,
original terminal states, repair indicators, and the SHA256 of each original
local result file. The hashes identify local evidence; original event streams
are not bundled and cannot be reconstructed from hashes. Reasons are model
self-reports, not adjudications or internal reasoning traces.

`data/attempt_ledger.json` contains the frozen telemetry reconstruction for
formal calls, including incomplete usage. It reproduces reported token costs;
it is not an invoice. The packet excludes executor usage and preparatory calls.
`COLLECTION_FREEZE.json` in this package is an explicitly reduced public
projection of configurations, batches, counts and seeds, not the original
signed/tag-bound local certificate.

The analysis bootstrap seed follows SHA256(`20261108:bootstrap`), first eight
hex digits as an integer. The independent simulation confirmation seed is
20261109. Exploratory supplemental intervals use a separate 20261109 stream;
they are unadjusted for multiplicity and do not change the frozen decision.

Before publication, the complete local data passed `[1,2,3]` eligibility for
each model. The public reproduction checks planned counts, exact source
statistics and normalization; it does not certify the original sandbox or
provider identity. See the report for bounded probe claims and runtime changes.

## Dependency-sensitive reproduction

The pinned Python 3.12.12 / NumPy 1.26.4 / SciPy 1.13.1 run matched all 2,958
comparable leaf fields and both frozen decisions. Four metadata keys exist only
in the saved results: `all_observed_state_counts` and `outside_complete_prefix`
for each route. The analysis functions do not recompute these keys.

`python recheck_tolerant.py .` lists all differing leaves and one-sided keys
instead of stopping at the first difference. The pinned run is recorded in
[`evidence/reproduction_pinned.txt`](evidence/reproduction_pinned.txt).
An external reviewer reported 36 interval-endpoint differences under Python
3.13.18 / NumPy 2.5.3 / SciPy 1.18.1, with a maximum absolute change of about
0.89 percentage points; point estimates and frozen choices matched. That run
has not been independently repeated here. The cause is unresolved: exact
reproduction is established for the pinned environment, not all versions.

## Lean notation evidence

[`evidence/lean/`](evidence/lean/README.md) contains a tested Lean 4.8.0 probe
for the binding scope in cc_0335 and the false original / true parenthesized
closed expressions in cc_0336, with the Mathlib revision and output. It preserves
the source `in` syntax. Type inspection of the original cc_0335 theorem uses a
placeholder; the separate `rfl` and `decide` proofs do not depend on it.
This is not a packaged rerun of all 858 Lean tasks or a complete semantic
adjudication of the dataset.

## Pending review

- Independent mathematical adjudication of the selected cases.
- Human spot-check of error-type classifications.
- Independent human assessment of the completed AI-assisted 74-item technical review.
- Full Lean evidence/environment packaging if a later release requires it.

The external model reviews and local machine checks do not complete these tasks.

## Technical label sensitivity

`python label_sensitivity.py --check` validates the 74 saved review records,
recomputes both label scenarios with the existing statistical functions and
checks all original point estimates against the frozen results. It also
exhaustively verifies the finite counterexample for cc_0790. Seed 20261110 and
10,000 draws are used separately for each scenario/model; this draw order is
new, so published-scenario intervals here need not exactly match frozen intervals.
The label judgments themselves are written inputs, not produced or validated
by the numerical script. No model calls are made.
