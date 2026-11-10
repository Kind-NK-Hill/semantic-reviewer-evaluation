"""Recompute the exploratory findings added after the November 10 review.

No model calls, label changes or imports from the frozen analysis implementation.
The C1 bootstrap follows the external reviewer's script: default_rng(5),
10,000 item-level percentile draws, model/comparison/subgroup order below.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

import numpy as np

ROOT = Path(__file__).resolve().parent
MAIN = {'R0', 'R1', 'R1g'}
SCOPE_SIX = ['cc_0328', 'cc_0335', 'cc_0336', 'cc_0379', 'cc_0435', 'cc_0467']


def read(name):
    return [json.loads(line) for line in (ROOT / name).read_text(encoding='utf-8').splitlines()]


def compute():
    items = read('data/processed/items.jsonl')
    records = read('data/judgments.jsonl')
    categories = {r['id']: r['category'] for r in read('labels/categories.jsonl')}
    pos = {item['id']: i for i, item in enumerate(items)}
    false = np.array([item['label'] == 'false' for item in items])
    cats = np.array([categories.get(item['id'], 'NA') for item in items])
    matrices = {}
    all_votes, main_votes = defaultdict(Counter), defaultdict(Counter)
    by_route = defaultdict(lambda: defaultdict(Counter))
    for row in records:
        job = row['job']
        key = row['model'], job['config']
        matrix = matrices.setdefault(key, np.full((len(items), 3), np.nan))
        if row['state'] != 'valid' or not row.get('parsed'):
            continue
        verdict = row['parsed']['verdict']
        item_id = job['item_id']
        matrix[pos[item_id], job['repetition'] - 1] = float(verdict == 'faithful')
        all_votes[item_id][verdict] += 1
        if job['config'] in MAIN:
            main_votes[item_id][verdict] += 1
            by_route[item_id][f'{row["model"]}/{job["config"]}'][verdict] += 1

    unanimous = sorted(item['id'] for item in items if item['label'] == 'false'
                       and all_votes[item['id']]['faithful'] == 25
                       and sum(all_votes[item['id']].values()) == 25)
    false_accepts = sum(main_votes[item['id']]['faithful'] for item in items if item['label'] == 'false')
    unanimous_main_accepts = sum(main_votes[i]['faithful'] for i in unanimous)
    queue = []
    for item in items:
        opposite = 'faithful' if item['label'] == 'false' else 'unfaithful'
        counts = main_votes[item['id']]
        if counts[opposite] >= 13:
            queue.append({'id': item['id'], 'source': item['source'], 'published_label': item['label'],
                          'main_votes': dict(counts), 'by_route_config': dict(by_route[item['id']]),
                          'adjudication': 'pending'})
    queue.sort(key=lambda x: x['id'])
    queue_hash = hashlib.sha256(('\n'.join(q['id'] for q in queue) + '\n').encode()).hexdigest()

    rng = np.random.default_rng(5)

    def summary(values):
        boot = values[rng.integers(0, len(values), (10000, len(values)))].mean(axis=1)
        low, high = np.percentile(boot, [2.5, 97.5])
        return {'n_items': len(values), 'difference_pp': 100 * float(values.mean()),
                'ci95_pp': [100 * float(low), 100 * float(high)]}

    comparisons = []
    for model in ('terra', 'flash'):
        for new, old in (('R1', 'R0'), ('R1g', 'R1')):
            difference = np.nanmean(matrices[model, new], axis=1) - np.nanmean(matrices[model, old], axis=1)
            comparisons.append({'model': model, 'comparison': f'{new}-{old}',
                                'C1': summary(difference[false & (cats == 'C1')]),
                                'other': summary(difference[false & (cats != 'C1')])})

    scope_cases, big_operator_cases = [], []
    for item in items:
        if any(re.search(r'parenthes|scope', reason, re.I) for reason in item['human_reasons']):
            scope_cases.append({'id': item['id'], 'published_label': item['label'],
                                'human_reasons': item['human_reasons'],
                                'all_valid_votes': dict(all_votes[item['id']])})
            if any(re.search(r'parenthes|scope of production', reason, re.I) for reason in item['human_reasons']):
                assert '∏' in item['formal_statement'] or '∑' in item['formal_statement']
                big_operator_cases.append(scope_cases[-1])
    scope_counts = sum((all_votes[i] for i in SCOPE_SIX), Counter())
    raw_counts, unique_counts = defaultdict(Counter), defaultdict(Counter)
    for item in items:
        raw_counts[item['source']][item['label']] += len(item['raw_rows'])
        unique_counts[item['source']][item['label']] += 1
    return {'scope': 'exploratory; published labels unchanged; categories not human-validated',
            'bootstrap': {'seed': 5, 'draws': 10000, 'interval': 'percentile 95%; unadjusted'},
            'C1_comparisons': comparisons,
            'unanimous_false_labeled': {'ids': unanimous, 'count': len(unanimous),
                'main_false_accept_votes': false_accepts, 'these_items_main_accept_votes': unanimous_main_accepts,
                'share_of_main_false_accept_votes': unanimous_main_accepts / false_accepts},
            'priority_review': {'rule': 'R0/R1/R1g, both routes, three repetitions; >=13 explicitly opposite votes',
                'counts_by_published_label': dict(Counter(q['published_label'] for q in queue)),
                'ordered_ids_sha256': queue_hash, 'items': queue},
            'scope_reason_matches': scope_cases,
            'big_operator_reason_matches': big_operator_cases,
            'scope_six': {'ids': SCOPE_SIX, 'valid_votes': sum(scope_counts.values()), 'verdicts': dict(scope_counts)},
            'raw_counts_from_provenance_rows': dict(raw_counts), 'unique_counts': dict(unique_counts)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Compare with the saved exploratory result')
    args = parser.parse_args()
    result = compute()
    out = ROOT / 'recomputed' / 'post_review.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.check:
        expected = json.loads((ROOT / 'results/post_review.json').read_text(encoding='utf-8'))
        assert result == expected, 'Post-review results differ; use the pinned environment and inspect recomputed/post_review.json'
    print(json.dumps({'C1_comparisons': result['C1_comparisons'],
                      'unanimous': result['unanimous_false_labeled']['count'],
                      'priority_review': result['priority_review']['counts_by_published_label'],
                      'scope_six': result['scope_six'],
                      'big_operator_cases': len(result['big_operator_reason_matches']),
                      'broader_scope_mentions': len(result['scope_reason_matches']),
                      'output': str(out.relative_to(ROOT))}, ensure_ascii=False, indent=2))
