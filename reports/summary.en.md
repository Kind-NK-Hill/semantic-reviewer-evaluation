# Evaluation summary — v0.4

This study calibrates a semantic reviewer against 858 unique externally labeled
natural-language/Lean-statement pairs. The published reference contains 570
faithful and 288 unfaithful items. Two model routes complete three repetitions;
wording controls and a Terra-only ablation bring the total to 19,170 calls.

The task excludes the proof. R0 is a minimal instruction, R1 contains six
adapted semantic review criteria, and R1g adapts the ReForm prompt used by the
benchmark's originating work to evaluate reviewers on ConsistencyCheck. It is a
paper baseline, not a benchmark-independent general prompt. Its gains may partly
reflect alignment with the benchmark's judgment conventions; this is a possible
explanation, not an established mechanism or evidence of data leakage.
Requested routes are `gpt-6.1-terra` with medium effort and `deepseek-flash` with
max effort. These are not matched compute budgets, and per-response backend
identity was not independently observable.

| Route | Prompt | False acceptance | False rejection/abstention |
|---|---|---:|---:|
| Terra | R0 |23.03%|8.36%|
| Terra | R1 |23.15%|9.82%|
| Terra | R1g |17.13%|10.70%|
| DeepSeek | R0 |30.79%|3.68%|
| DeepSeek | R1 |24.54%|5.38%|
| DeepSeek | R1g |18.52%|5.61%|

Estimates average repeated judgments within each item. Comparisons are paired
by item; intervals use 10,000 cluster percentile bootstrap draws. Reported
intervals are 95%; the frozen noninferiority test uses the upper endpoint of a
97.5% two-sided interval, with a five-percentage-point margin on both error
measures. Explicit error detection must also improve before R1 is called
superior to R0.

The frozen comparison first tests whether R1 significantly reduces false
acceptance. If so, it returns superiority only when explicit detection also
improves; otherwise it records more rejection/abstention and stops that branch.
Only when the false-acceptance branch is not triggered does it test the
alternative's noninferiority. The first draft incorrectly described
noninferiority as having priority. Code and the original protocol agree, and
neither observed result lies in the overlap region, so both choices remain
unchanged: R0 for Terra and R1g for DeepSeek. These are candidate-replacement
conclusions under the registered rule, not global deployment optima. The tree
does not directly choose between Terra R0 and R1g. DeepSeek's R1 advantage over
R0 is not established in the ProofNet-only sensitivity analysis.

An explicitly exploratory direct Terra comparison, added after review, gives
R1g-minus-R0 differences of -5.90 percentage points in false acceptance
(95% interval [-8.68,-3.36]) and +2.34 in false rejection ([1.23,3.51]). Under
the current item mix, this means 17 fewer false accepts and 13.33 more false
rejects per average full pass. Ignoring call and review costs, a linear-loss
point estimate favors R1g when a false accept costs more than about 0.78 false
rejects. This is a hypothetical tradeoff, not an observed business weight.

Repeated agreement is not independent confirmation. Under R1, 59 Terra and 54
DeepSeek unfaithful items are accepted on all three calls. Majority voting
changes false acceptance little; unanimous acceptance reduces false acceptance
while increasing false rejection. Exploratory first-repetition combinations
show 55 shared misses under R1, with 11 and 16 additional explicit detections
provided by the other reviewer. These are offline policy replays, not deployed
multi-agent workflow results.

The November 10 review exposed heterogeneity hidden by the aggregate. Terra's
R1-minus-R0 false-acceptance difference is +7.78 percentage points on 60 items
categorized as missing a premise (95% interval [2.22,13.89]) and -1.90 on the
other 228 ([-3.80,-0.29]). R1g-minus-R1 differences are -18.33 and -2.78 for
Terra, and -13.33 and -4.09 for DeepSeek. These are post-hoc subgroup estimates
using model-assigned categories that still require human checking; intervals
are unadjusted. `post_review.py --check` reproduces the added results.

Twenty-six false-labeled items are accepted in every one of their 25 valid
judgments. They account for 468 of 1,185 main-comparison false-accept votes
(39.5%), but contribute zero to within-item prompt differences. This motivates
targeted review, not automatic relabeling. A saved 74-item queue selects at least
13 explicitly label-opposing verdicts among the 18 main-comparison votes:
48 false-labeled and 26 true-labeled items. It is not a random label-error audit.

Two notation cases now have direct Lean evidence. With the original `in`
syntax under Lean 4.8.0, cc_0335's product body ends before the addition and
the remaining `k` becomes an implicit real parameter. A separate `rfl` proof
checks the expansion. For cc_0336, `decide` proves the original closed expression
false and the parenthesized expression true. Six related items receive 148
acceptances across 150 judgments. This count alone does not establish the
models' internal mechanism or the effect of repairing their input; no new
model experiment was run. Source, Mathlib revision and output are published
in `evidence/lean/`.

The revised report also compares matched replay costs from the actual selected
attempts. Terra R1g once misses 47 items and rejects 66 faithful items, versus
59/66 for Terra R1 unanimous-three; their observed costs are 53.99 and 145.33
credits, with six unknown-charge attempts in the latter. DeepSeek R1g once and
dual-model R1 once both miss 55 items, but reject 29 and 58 faithful items. Recorded
costs are 4.36 CNY versus 50.08 credits plus 4.77 CNY, respectively; currencies are
not combined. Cache/retry histories differ, so these are not prospective cost
estimates or randomized efficiency effects. More calls do not automatically
buy a better operating point, but universal superiority is not established.

Collection initially recorded 114 invalid JSON escapes for DeepSeek. An
author-approved deterministic reader repairs only illegal backslashes in the
reason string; original outputs are preserved. One tool-use record remains
excluded. All final batches satisfy the existing quality criteria after this
normalization. Prompt, label and statistical decision rules were not changed
in response to interim results. Concurrency and collection continuation were
amended during collection and are disclosed.

Restoring repaired answers to missing preserves the numerical DeepSeek choice
in a post-review sensitivity calculation, but the original strict raw records
still fail the 2% quality gate. If all raw invalid votes instead block acceptance,
R0/R1/R1g false rejection becomes 6.02%/6.55%/6.26%, versus the repaired semantic
estimates 3.68%/5.38%/5.61%. Numerical robustness and pipeline eligibility are
different questions; a single missing record after repair does not establish
that repair was irrelevant.

The simulation program originally failed one acceptance cell at 44/1,000.
Diagnosis found no effect offset from the intended five-point boundary, but a
1.04368 ratio of empirical variation to conditional bootstrap standard error.
The author chose the conservative noninferiority interval before formal
outcomes, retained percentile intervals, and rejected post-hoc selection of
the studentized candidate. An independent seed passed the original simulation
acceptance criteria. Exact binomial intervals and all candidate results are
bundled; the simulation does not prove a population error rate below 4%.

Pilot, control and repetition items overlap the formal set by 98/100, 58/60 and
19/20. They are not independent validation data. Ten ablation prechecks were
all unfaithful items and established only that the route could answer.

The findings support bounded reviewer configuration decisions and expose
persistent/shared error. They do not certify the published labels, establish
general optimal rules, explain historical model failures, or demonstrate
improved end-to-end formalization. The original case records are retained;
the three specific label questions are now resolved in the technical review
below, with item-level reasoning and machine evidence.

## Label review completed after the initial analysis

The 74-item targeted queue now has a written rubric, item-level explanations,
repair suggestions and a label-sensitivity replay over all 858 items. There
are 37 acceptable statements, 23 unfaithful statements and 14 convention or
context cases. Compared with the source, 33 false labels become true and 15
true labels become false; 12 reviewed labels agree and the 14 convention cases
retain their source labels. The resulting scenario has 588 faithful and 270
unfaithful items. Of the 26 unanimously accepted false-labeled items, 18 are
acceptable, five retain substantive binding errors and three are convention cases.

R0/R1/R1g false acceptance becomes 12.35/12.84/6.79% for Terra and
22.47/15.31/10.37% for DeepSeek. False rejection becomes 5.56/7.14/8.16%
and 1.87/3.29/4.20%, respectively. The frozen rule, replayed post hoc, still
selects Terra R0 and DeepSeek R1g. The original results remain separately available.

Evidence includes 29 checked local Lean lemmas without placeholders, six
original elaborated headers, a version-specific type-error probe and an
exhaustively checked finite counterexample. Review was AI-assisted and conducted
with labels and model disagreements visible. It is not independent human
adjudication and cannot estimate population label-error prevalence. Bootstrap
intervals condition on the chosen labels. Detailed reasoning and all intervals
are linked in the [review appendix](technical-label-review.zh-CN.md).
