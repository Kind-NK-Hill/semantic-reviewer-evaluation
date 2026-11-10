"""Field-by-field comparison of a fresh recomputation against results/main_results.json.

Unlike reproduce.py, this does not stop at the first mismatch: it lists every
differing leaf with both values, plus keys present on only one side.
It calls the repository's own analysis code (src/analysis_core.analyze_model)
with the frozen settings and seed; it changes nothing in the repository.

Usage:  python recheck_tolerant.py /path/to/semantic-reviewer-evaluation [out.json]
"""
import json, math, os, sys
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[v] = "1"
repo = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.join(repo, "src"))
import numpy as np, scipy
from adapter import ROOT, load, read_jsonl
from analysis_core import analyze_model

settings = load(ROOT / "protocol/analysis_settings.json")
os.environ["RC_BOOTSTRAP_METHOD"] = settings["bootstrap_method"]
os.environ["RC_NONINFERIORITY_COVERAGE"] = str(settings["noninferiority_coverage"])
records = read_jsonl(ROOT / "data/judgments.jsonl")
items = read_jsonl(ROOT / "data/processed/items.jsonl")
expected = load(ROOT / "results/main_results.json")["models"]
seed = load(ROOT / "COLLECTION_FREEZE.json")["seeds"]["bootstrap"]

diffs, one_sided, leaves = [], [], [0]

def compare(new, old, path):
    if isinstance(new, dict) and isinstance(old, dict):
        for key in sorted(set(new) | set(old)):
            if key not in new or key not in old:
                one_sided.append((f"{path}.{key}", "recomputed only" if key in new else "frozen only"))
            else:
                compare(new[key], old[key], f"{path}.{key}")
    elif isinstance(new, list) and isinstance(old, list):
        if len(new) != len(old):
            diffs.append((path, f"len {len(new)}", f"len {len(old)}"))
        for i, (x, y) in enumerate(zip(new, old)):
            compare(x, y, f"{path}[{i}]")
    else:
        leaves[0] += 1
        numeric = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
        if numeric(new) and numeric(old):
            if not math.isclose(new, old, rel_tol=1e-10, abs_tol=1e-12):
                diffs.append((path, new, old))
        elif new != old:
            diffs.append((path, new, old))

out = {}
for model in ("terra", "flash"):
    subset = [r for r in records if r["model"] == model]
    out[model], _ = analyze_model(subset, items, [1, 2, 3], np.random.default_rng(seed))
    compare(out[model], expected[model], model)

print(f"python {sys.version.split()[0]}  numpy {np.__version__}  scipy {scipy.__version__}")
print(f"leaves compared: {leaves[0]}   differing: {len(diffs)}   keys on one side only: {len(one_sided)}")
for path, new, old in diffs:
    if isinstance(new, float) and isinstance(old, float):
        print(f"DIFF {path}\trecomputed={new:.6f}\tfrozen={old:.6f}\tdiff_pp={100 * (new - old):+.4f}")
    else:
        print(f"DIFF {path}\trecomputed={new}\tfrozen={old}")
for path, side in one_sided:
    print(f"KEY  {path}\t{side}")
print("decisions:", {m: out[m]["decision"] for m in out}, "| frozen:", {m: expected[m]["decision"] for m in out})
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
