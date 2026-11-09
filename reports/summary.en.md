# Evaluation summary — draft v0.1

This study calibrates a semantic reviewer against858 unique externally labeled
natural-language/Lean-statement pairs. The published reference contains570
faithful and288 unfaithful items. Two model routes complete three repetitions;
wording controls and a Terra-only ablation bring the total to19,170 calls.

The task excludes the proof. R0 is a minimal instruction, R1 contains six
adapted semantic review criteria, and R1g is an adapted general review prompt.
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
by item; intervals use10,000 cluster percentile bootstrap draws. Reported
intervals are95%; the frozen noninferiority test uses the upper endpoint of a
97.5% two-sided interval, with a five-percentage-point margin on both error
measures. Explicit error detection must also improve before R1 is called
superior to R0.

The frozen decision tree selects R0 for Terra and R1g for DeepSeek. It prioritizes
acceptable simplification, not the globally lowest false-accept point estimate.
Terra's R1g has lower false acceptance than R1, but this does not override the
tree's earlier R0 branch. DeepSeek's R1 advantage over R0 is not established in
the ProofNet-only sensitivity analysis, limiting source-level generalization.

Repeated agreement is not independent confirmation. Under R1,59 Terra and54
DeepSeek unfaithful items are accepted on all three calls. Majority voting
changes false acceptance little; unanimous acceptance reduces false acceptance
while increasing false rejection. Exploratory first-repetition combinations
show55 shared misses under R1, with11 and16 additional explicit detections
provided by the other reviewer. These are offline policy replays, not deployed
multi-agent workflow results.

Collection initially recorded114 invalid JSON escapes for DeepSeek. An
author-approved deterministic reader repairs only illegal backslashes in the
reason string; original outputs are preserved. One tool-use record remains
excluded. All final batches satisfy the existing quality criteria after this
normalization. Prompt, label and statistical decision rules were not changed
in response to interim results. Concurrency and collection continuation were
amended during collection and are disclosed.

The simulation program originally failed one acceptance cell at44/1,000.
Diagnosis found no effect offset from the intended five-point boundary, but a
1.04368 ratio of empirical variation to conditional bootstrap standard error.
The author chose the conservative noninferiority interval before formal
outcomes, retained percentile intervals, and rejected post-hoc selection of
the studentized candidate. An independent seed passed the original simulation
acceptance criteria. Exact binomial intervals and all candidate results are
bundled; the simulation does not prove a population error rate below4%.

Pilot, control and repetition items overlap the formal set by98/100,58/60 and
19/20. They are not independent validation data. Ten ablation prechecks were
all unfaithful items and established only that the route could answer.

The findings support bounded reviewer configuration decisions and expose
persistent/shared error. They do not certify the published labels, establish
general optimal rules, explain historical model failures, or demonstrate
improved end-to-end formalization. Fifteen cases remain unadjudicated. Full
Chinese draft, frozen outputs and offline reproduction accompany this summary.
