# Reproduction scope

The package reproduces analysis from completed judgments. It does not make new
model calls, recover hidden provider state, rerun Lean, or independently judge
semantic labels. Python3.12 and pinned dependencies are recorded in
`requirements.txt`.

1. `python verify_release.py` verifies the allowlisted publication files.
2. `python reproduce.py` checks all19,170 unique records, validates114 repairs,
   recomputes the frozen model-level statistics and checks every returned field.
3. `python supplement.py` computes the explicitly exploratory repeat-policy,
   matched-transition and cross-model diagnostics.

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
20261109. Exploratory supplemental intervals use a separate20261109 stream;
they are unadjusted for multiplicity and do not change the frozen decision.

Before publication, the complete local data passed `[1,2,3]` eligibility for
each model. The public reproduction checks planned counts, exact source
statistics and normalization; it does not certify the original sandbox or
provider identity. See the report for bounded probe claims and runtime changes.

## Pending review

- Independent mathematical adjudication of the selected cases.
- Human spot-check of error-type classifications.
- External interpretation review of this first draft.
- Full Lean evidence/environment packaging if a later release requires it.

These are stated limitations of the first draft, not completed validation.
