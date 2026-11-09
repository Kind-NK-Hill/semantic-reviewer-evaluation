import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
USAGE_FIELDS=('input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens')
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def read_jsonl(path):return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
def attempt_ledger():return load(ROOT/'data/attempt_ledger.json')

def summarize_attempts(rows):
    starts=[r['started'] for r in rows if r['started'] is not None];ends=[r['ended'] for r in rows if r['ended'] is not None]
    return {'attempts':len(rows),'distinct_calls':len({(r['stage'],r['model'],r['key']) for r in rows}),
            'states':dict(Counter(r['state'] for r in rows)),
            'known_usage':{field:sum(r['usage'][field] for r in rows if field in r['usage']) for field in USAGE_FIELDS},
            'attempts_without_usage_field':{field:sum(field not in r['usage'] for r in rows) for field in USAGE_FIELDS},
            'attempts_with_unknown_charge':sum(r['possible_charge_unknown'] for r in rows),
            'sum_observed_attempt_seconds':sum(r['seconds'] for r in rows if r['seconds'] is not None),
            'attempts_without_duration':sum(r['seconds'] is None for r in rows),
            'elapsed_window_seconds':max(ends)-min(starts) if starts and ends else None,
            'usage_scope':'Sums of observed usage only; missing fields and possibly charged interruptions are counted separately, never assumed zero.',
            'currency_or_credits':'not_observable; no conversion rate recorded'}
