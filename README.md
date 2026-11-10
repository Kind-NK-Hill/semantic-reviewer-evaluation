# When can a semantic reviewer be trusted?

**Rules, repeated judgments, and second opinions in mathematical formalization**

Shuo Deng · Evaluation report v0.4 · 10 November 2026

[中文评估报告](reports/evaluation-draft.zh-CN.md) · [English summary](reports/summary.en.md) · [中文项目说明](README.zh-CN.md) · [Results](results/main_table.csv)

A theorem can compile while expressing the wrong problem. A model reviewer can
also give the same wrong answer three times. This study calibrates a semantic
review component against externally published labels, asking what prompt rules,
repeated checks, and a second model actually change.

The complete collection contains **858 unique inputs and 19,170 judgments** from
two model routes. There are 570 faithful and 288 unfaithful items; repeated calls
are not independent mathematical tasks. All three planned batches are complete.

## Findings to inspect

- **The six-rule prompt has model-dependent value.** Terra's mean false-accept
  rates are 23.03% with the minimal prompt and 23.15% with six rules. DeepSeek's
  corresponding rates are 30.79% and 24.54%. The frozen selection rule chooses
  the minimal prompt for Terra and the adapted ReForm benchmark-review prompt
  for DeepSeek. These are registered-rule outcomes, not global deployment optima.
- **Stable judgments can persistently disagree with labels.** Under the six-rule
  prompt, 59/288 Terra items and 54/288 DeepSeek false-labeled items are accepted on all three calls.
  Majority voting offers limited improvement. Requiring unanimous acceptance
  reduces false acceptance while increasing rejection of faithful items.
- **A second opinion adds information but shares blind spots.** On the fixed
  first repetition, the two six-rule reviewers jointly miss 55 unfaithful items.
  DeepSeek explicitly detects 11 misses of Terra; Terra explicitly detects 16
  misses of DeepSeek. This is an exploratory offline combination, not a tested
  multi-agent repair workflow.
- **Measurement failures matter.** A deterministic, author-approved reader
  recovers 114 invalid JSON escapes; one unverified tool-use record stays
  excluded. Original states remain available, and the repair can be replayed.
- **Changing the prompt can beat more checks in the observed sample.** Terra
  R1g once misses 47 items and rejects 66 faithful items, versus 59/66 for R1
  unanimous-three. The revised report compares exact selected-call accounting
  and directly estimates Terra R1g-versus-R0 risk; it does not assume business
  error costs or claim universal superiority of one replay policy.

## Read and reproduce

The November 10 review adds two findings. Terra's near-zero R1-minus-R0 average
combines a +7.78 percentage-point false-accept change on missing-premise items
with -1.90 on other items. Twenty-six false-labeled items are accepted in all
25 judgments, motivating a targeted label review. Separately, a Lean probe
establishes an escaped variable in cc_0335 and refutes cc_0336's original closed
expression while proving its parenthesized counterpart. See the
[follow-up record](reports/review-followup.md) and [machine evidence](evidence/lean/README.md).

| Purpose | File |
|---|---|
| Read the evaluation report | [Chinese report](reports/evaluation-draft.zh-CN.md) |
| Inspect frozen estimates, intervals and decisions | [Results JSON](results/main_results.json) |
| Inspect exploratory reliability and second opinions | [Supplement JSON](results/supplement.json) |
| Read the actual prompts | [Prompt templates](prompts/) |
| Inspect the original 15 case records | [Case record](reports/key_cases.md) |
| Read 74 technical reviews and label sensitivity | [Technical review](reports/technical-label-review.zh-CN.md) |
| Inspect the new subgroup results and 74-item review queue | [Post-review results](results/post_review.json) |
| Check simulation failures and confirmation | [Simulation rates](protocol/simulation-rates.md) |
| Understand sources, exclusions and release scope | [Reproducibility](REPRODUCIBILITY.md), [provenance](protocol/provenance.json), [third-party notice](THIRD_PARTY_NOTICES.md) |

Python 3.12; no API keys or model access required:

```sh
python -m pip install -r requirements.txt
python verify_release.py
python reproduce.py
python supplement.py
python post_review.py --check
python label_sensitivity.py --check
```

`reproduce.py` reruns the unchanged frozen statistical function bodies with
portable file inputs and checks every reproduced field against the saved
results. It also verifies all 114 escape repairs. The supplement uses an explicitly
separate exploratory stream and never changes the registered decision tree.
Post-review additions include a direct Terra R1g-minus-R0 comparison, exact
selected-attempt costs, and raw-output sensitivity; both the seed and the
quality-gate eligibility limits are recorded in the supplement.

## Scope and relationship to earlier work

This evaluation is related to the
[formalization engine](https://github.com/Kind-NK-Hill/ProbabilityTheoryFormalization)
and the [66-run workflow evaluation](https://github.com/Kind-NK-Hill/review-history-evaluation).
It supplies external calibration for one reviewer component. It does not
establish improved proof repair, autonomous planning, tool-feedback use, or
end-to-end completion in that engine. The tested six-rule prompt is adapted,
not a replay of the complete production reviewer.

Original error rates use published labels; the technical-review scenario is reported separately. External model reviews informed
the revision; the 74-item technical review is complete. The author defined the
study decisions; AI tools assisted implementation, execution, analysis and
drafting. The draft makes no claim of independent mathematical certification.

The repository is a clean publication snapshot. Credentials, private chats,
internal reasoning streams, account configuration, and the working repository's
history are excluded. See [release notes](CHANGELOG.md).

## Completed targeted technical review

The 74-item queue now has item-level reasoning and repair suggestions: 37
acceptable, 23 unfaithful, and 14 convention/context cases. The sensitivity
scenario changes 33 false labels to true and 15 true labels to false across
all 858 items; it keeps convention cases and all unreviewed labels unchanged.
Absolute error rates change substantially, while the rule still selects R0
for Terra and R1g for DeepSeek. This is a post-hoc AI-assisted technical review
with mathematical and machine evidence, not an independent human gold set.
See [findings and evidence](reports/technical-label-review.zh-CN.md) and
[recomputed results](results/label_sensitivity.json).
