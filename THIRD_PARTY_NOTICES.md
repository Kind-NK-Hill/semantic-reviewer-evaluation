# Data, prompts and related projects

The semantic reference is ConsistencyCheck at commit
`1c6a6cca0f87b48d4cccb49946d3b8fc57a1eef9`:
https://huggingface.co/datasets/GuoxinChen/ConsistencyCheck/tree/1c6a6cca0f87b48d4cccb49946d3b8fc57a1eef9

Its dataset card declares the MIT license. The benchmark is associated with
REFORM and contains source labels for miniF2F and ProofNet. Original text,
formal statements and annotation reasons retain their upstream attribution.
This project does not claim authorship of those mathematical tasks or labels.

The separate ProofNetVerif reference snapshot used in preparatory checking is
at commit `91183e5b12d64374827bf2782db629b5b0f8f319`:
https://huggingface.co/datasets/PAug/ProofNetVerif/tree/91183e5b12d64374827bf2782db629b5b0f8f319
It is not a second independent main sample in this evaluation.

R1 is an adaptation of semantic requirements from the author's formalization
project; R1g adapts a public general consistency-check prompt. Original prompt
templates and the preparation source documenting transformations are included.
These are experimentally different prompt packages, not an isolated test of
one principle.

Related author projects:
- https://github.com/Kind-NK-Hill/ProbabilityTheoryFormalization
- https://github.com/Kind-NK-Hill/review-history-evaluation

This initial private draft does not grant a new blanket license over
third-party data, model outputs or the related projects. Their existing terms
remain applicable. Publication/licensing decisions can be made separately
before a public release.
