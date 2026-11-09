"""Author-approved, local-only repair of illegal JSON escapes in reason strings.

Never edits raw result/event files, never calls a model, and never guesses verdicts.
"""
import hashlib
import json
from collections import Counter, defaultdict
import jsonschema

RULE = 'reason-invalid-json-escape-v1'
SCHEMA = {'type':'object','properties':{'verdict':{'type':'string','enum':['faithful','unfaithful','uncertain']},'reason':{'type':'string'}},'required':['verdict','reason'],'additionalProperties':False}


def repair_reason(text):
    """Return a validated copy and original character offsets, or None.

    Parse the top-level structure strictly; only scan reason's string tolerantly.
    Legal escapes (including unicode escapes) are never changed. Duplicate keys,
    illegal escapes outside reason, and all other syntax/schema errors fail closed.
    """
    try:
        json.loads(text)
        return None  # Strictly parseable JSON never needs this repair.
    except (ValueError, TypeError):
        if not isinstance(text,str):return None
    decoder=json.JSONDecoder();i=0;positions=[];seen=set()
    def ws(pos):
        while pos<len(text) and text[pos] in ' \t\r\n':pos+=1
        return pos
    try:
        i=ws(i)
        if text[i]!='{':return None
        i=ws(i+1)
        while True:
            key,end=decoder.raw_decode(text,i)
            if key not in ('verdict','reason') or key in seen:return None
            seen.add(key);i=ws(end)
            if text[i]!=':':return None
            i=ws(i+1)
            if key=='reason':
                if text[i]!='"':return None
                i+=1
                while True:
                    ch=text[i]
                    if ch=='"':i+=1;break
                    if ch=='\\':
                        nxt=text[i+1]
                        if nxt not in '"\\/bfnrtu':positions.append(i)
                        i+=2
                    else:i+=1
            else:
                value,i=decoder.raw_decode(text,i)
                if not isinstance(value,str):return None
            i=ws(i)
            if text[i]=='}':i=ws(i+1);break
            if text[i]!=',':return None
            i=ws(i+1)
        if i!=len(text) or seen!={'verdict','reason'} or not positions:return None
        fixed=text
        for pos in reversed(positions):fixed=fixed[:pos]+'\\'+fixed[pos:]
        obj=json.loads(fixed);jsonschema.validate(obj,SCHEMA)
        return {'text':fixed,'parsed':obj,'inserted_backslash_offsets':positions}
    except (ValueError, TypeError, IndexError, jsonschema.ValidationError):return None


def normalize_record(record):
    if record.get('state')!='format_failure':return record
    # An alternate format failure must not hide a tool/observability/timeout issue.
    if record.get('timed_out') or record.get('pending_question'):return record
    if not record.get('completed_turn_observed'):return record
    tools=record.get('tools',{})
    if tools.get('malformed_event_lines'):return record
    if any(r.get('state')!='blocked' for r in tools.get('calls',[])+tools.get('stderr_evidence',[])):return record
    if record.get('reason')!='completed_turn_invalid_output':return record
    original=record.get('final_output','');fixed=repair_reason(original)
    if fixed is None:return record
    audit={'rule':RULE,'original_state':record['state'],'original_reason':record['reason'],
           'original_output_sha256':hashlib.sha256(original.encode('utf-8')).hexdigest(),
           'inserted_backslash_offsets':fixed['inserted_backslash_offsets'],
           'repaired_output':fixed['text']}
    return {**record,'state':'valid','reason':'validated_after_reason_escape_repair',
            'parsed':fixed['parsed'],'format_repair':audit}


def quality_for_jobs(records,jobs,labels):
    bykey={(r['model'],r['key']):r for r in records};groups=defaultdict(Counter)
    terminal={'valid','format_failure','tool_contaminated','final_missing'}
    rows=[bykey.get((j['model'],j['key'])) for j in jobs]
    complete=bool(jobs) and all(r and r['state'] in terminal for r in rows)
    for r in rows:
        if not r or r['state'] not in terminal:continue
        job=r['job'];g=groups[(job['config'],labels[job['item_id']])];g['total']+=1
        if r['state']!='valid':g['bad']+=1
    violations=[{'config':c,'label':label,**dict(v)} for (c,label),v in groups.items() if 100*v['bad']>2*v['total']]
    return {'complete':complete,'passed':complete and not violations,'violations':violations,
            'returned':sum(r is not None for r in rows),'planned':len(jobs),
            'states':dict(Counter(r['state'] for r in rows if r)),
            'repaired_calls':sum(bool(r and r.get('format_repair')) for r in rows)}


def audit_saved(generation=0):
    from common import ROOT,load,save,sha,stamp,read_jsonl
    from split_freeze import verify_analysis
    from schedule import main_jobs
    verify_analysis()
    stage=f'main/generation-{generation:02d}';records=[];raw_states=defaultdict(Counter);repairs=[]
    for path in sorted((ROOT/'runs'/stage).glob('*/*/result.json')):
        data=path.read_bytes();raw=json.loads(data);record=normalize_record(raw)
        raw_states[raw['model']][raw['state']]+=1;records.append(record)
        if record.get('format_repair'):
            repair={'source_path':str(path.relative_to(ROOT)),'source_sha256':hashlib.sha256(data).hexdigest(),
                    'model':raw['model'],'key':raw['key'],**record['format_repair']}
            repairs.append(repair)
            # Content-addressed derived artifact; raw result and event bytes untouched.
            target=ROOT/'analysis/format_repairs'/stage/raw['model']/raw['key']/(repair['source_sha256']+'.json')
            if not target.exists():save(target,repair)
            assert sha(path)==repair['source_sha256'],'Completed source changed during audit'
    labels={r['id']:r['label'] for r in read_jsonl(ROOT/'data/processed/items.jsonl')}
    quality={m:{str(b):quality_for_jobs(records,[j for j in main_jobs(b,generation) if j['model']==m],labels)
                for b in (1,2,3)} for m in ('terra','flash')}
    summary={'time':stamp(),'rule':RULE,'generation':generation,'snapshot_only':True,
             'scope':'Format states and quality gates only; no verdict rates calculated',
             'raw_state_counts':{m:dict(c) for m,c in raw_states.items()},
             'repaired_calls':dict(Counter(r['model'] for r in repairs)),
             'quality':quality,'raw_files_modified':False,'model_calls_started':0}
    save(ROOT/'analysis/format_repairs/latest_status.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
    return summary


if __name__=='__main__':audit_saved()
