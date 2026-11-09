"""Phase scheduler, durable progress and model-specific exhaustion handling."""
from __future__ import annotations
import argparse
from collections import Counter,deque
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from common import ROOT,read_jsonl,save,load,stamp,rng,DEADLINE,now,note
from experiment_runner import invoke,render,STATE,append,safe_job,network_recoverable,interrupted_result
from prepare_prompts import ablation
from process_guard import SchedulerLock

def make_job(stage,model,config,item,rep=1,batch=0):
    key=f'b{batch}-{config}-{item["id"]}-r{rep}'
    return {'stage':stage,'model':model,'config':config,'item_id':item['id'],'repetition':rep,'batch':batch,'key':key,
            'schema':'prompts/verdict.schema.json','prompt':render(config,item)}

def labels_jobs():
    prompt=(ROOT/'labels/error_type_prompt.txt').read_text(encoding='utf-8')
    return [{'stage':'labels','model':'terra','config':'category','item_id':r['id'],'repetition':1,'batch':0,'key':f'category-{r["id"]}',
             'schema':'labels/category.schema.json','prompt':prompt+'\n\n'+r['human_reasons'][0]}
            for r in read_jsonl(ROOT/'data/processed/items.jsonl') if r['type_eligible']]

def pilot_jobs():
    jobs=[]
    for item in read_jsonl(ROOT/'data/processed/pilot.jsonl'):
        for config in ['R0','R1','R1g','R0a','R0b']:
            for model in ['terra','flash']:jobs.append(make_job('pilot',model,config,item))
    for item in read_jsonl(ROOT/'data/processed/controls.jsonl'):
        for config in ['R0','R1','R1g']:
            for model in ['terra','flash']:jobs.append(make_job('pilot',model,config,item))
    for item in read_jsonl(ROOT/'data/processed/repeat20.jsonl'):
        for config in ['R0','R1']:
            for rep in [1,2,3]:
                for model in ['terra','flash']:jobs.append(make_job('pilot',model,config,item,rep))
    if (ROOT/'prompts/R1-k.txt').exists():
        for item in read_jsonl(ROOT/'data/processed/ablation10.jsonl'):
            for model in ['terra','flash']:jobs.append(make_job('pilot',model,'R1-k',item))
    return jobs

def main_jobs(batch,generation=0,design=None):
    items=read_jsonl(ROOT/'data/processed/items.jsonl');gen=rng('item_order');gen.shuffle(items)
    configs=['R0','R1','R1g']+(['R1-k'] if (ROOT/'prompts/R1-k.txt').exists() else [])
    stage=f'main/generation-{generation:02d}'
    jobs=[]
    for item in items:
        if batch<=3:
            for config in configs:
                for model in ['terra','flash']:jobs.append(make_job(stage,model,config,item,batch,batch))
        if (batch==1 and item['label']=='false') or (batch==4 and item['label']=='true'):
            for config in ['R0a','R0b']:
                for model in ['terra','flash']:jobs.append(make_job(stage,model,config,item,1,batch))
    if design is None:
        path=ROOT/'COLLECTION_FREEZE.json'
        if path.exists():design=load(path)
    if design:
        from collection_rules import permitted
        jobs=[j for j in jobs if permitted(j,design)]
    return jobs

def run_jobs(jobs,workers,phase,*,supplement=False,network_resume=False):
    pending=deque(jobs);futures={};results=[];counts=Counter();started=time.time();last=0
    append(ROOT/'logs/scheduler_events.jsonl',{'event':'phase_started','phase':phase,'time':stamp(),'pid':os.getpid(),'jobs':len(jobs),'supplement':supplement})
    def progress(active):
        state={'time':stamp(),'pid':os.getpid(),'phase':phase,'supplement':supplement,'planned':len(jobs),'returned':len(results),
               'active':active,'status_counts':dict(counts),'exhausted_models':sorted(STATE.exhausted),'elapsed_seconds':time.time()-started,
               'deadline_utc':DEADLINE.isoformat(),'state':'running'}
        save(ROOT/'logs/heartbeat.json',state)
        save(ROOT/'logs'/f'{phase.replace("/","_")}_status.json',state)
        (ROOT/'logs/progress.md').write_text('# 当前进度\n\n```json\n'+json.dumps(state,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fatal=None
        while True:
            if jobs and jobs[0]['stage'].startswith('main/') and (ROOT/'logs/collection_stop.json').exists():
                pending.clear();fatal={'state':'mechanism_error','reason':'collection_stop_marker'}
            if now()>=DEADLINE:
                while pending:
                    job=pending.popleft();result=interrupted_result(job,'deadline')
                    results.append(result);counts[result['state']]+=1
                    append(ROOT/'logs/completions.jsonl',{'time':stamp(),'phase':phase,'key':result['key'],'model':result['model'],'state':result['state']})
            scanned=0;available=len(pending)
            while len(futures)<workers and pending and scanned<available and now()<DEADLINE and fatal is None:
                job=pending.popleft();scanned+=1
                if STATE.exhausted_model(job['model']):
                    result=interrupted_result(job,'quota_interrupted')
                    results.append(result);counts[result['state']]+=1
                    append(ROOT/'logs/completions.jsonl',{'time':stamp(),'phase':phase,'key':result['key'],'model':result['model'],'state':result['state']})
                    continue
                if STATE.delay(job['model'])>0:
                    if job['stage'].startswith('main/'):
                        from hardware_guard import GOVERNOR,enabled
                        if enabled():GOVERNOR.provider_pause(job['model'])
                    pending.append(job);continue
                if job['stage'].startswith('main/'):
                    from collection_rules import admission_delay
                    if admission_delay(job['model'])>0:pending.append(job);continue
                    from hardware_guard import GOVERNOR,enabled
                    if enabled() and len(futures)>=GOVERNOR.slots(job['model'],workers):
                        pending.appendleft(job);break
                futures[pool.submit(invoke,job,supplement=supplement,network_resume=network_resume)]=job
            if time.time()-last>=5:progress(len(futures));last=time.time()
            if not futures:
                if pending and now()<DEADLINE and fatal is None:time.sleep(1);continue
                break
            done,_=wait(futures,timeout=1,return_when=FIRST_COMPLETED)
            for future in done:
                job=futures.pop(future)
                try:result=future.result()
                except Exception as e:
                    result={'key':job['key'],'model':job['model'],'job':safe_job(job),'state':'mechanism_error','exception':type(e).__name__+': '+str(e)}
                if result['state']=='temporary_limit':pending.append(job)
                else:results.append(result);counts[result['state']]+=1
                if job['stage'].startswith('main/'):
                    from hardware_guard import GOVERNOR,enabled
                    if enabled():GOVERNOR.completed_call(job['model'],result)
                append(ROOT/'logs/completions.jsonl',{'time':stamp(),'phase':phase,'key':result['key'],'model':result['model'],'state':result['state']})
                if result['state'] in ('mechanism_error','authentication_blocked'):
                    fatal=result;save(ROOT/'logs/runner_blocker.json',{'time':stamp(),'phase':phase,'result':result})
                    if job['stage'].startswith('main/'):
                        save(ROOT/'logs/collection_stop.json',{'time':stamp(),'generation':0,'model':job['model'],'error':result.get('exception',result['state'])})
            if fatal:pending.clear()
    progress(0)
    summary={'time':stamp(),'phase':phase,'state':'failed' if fatal else 'deadline' if now()>=DEADLINE else 'finished',
             'counts':dict(counts),'returned':len(results),'planned':len(jobs),'elapsed_seconds':time.time()-started,'pid':os.getpid()}
    save(ROOT/'logs/heartbeat.json',summary);save(ROOT/'logs'/f'{phase.replace("/","_")}_summary.json',summary)
    append(ROOT/'logs/scheduler_events.jsonl',{'event':'phase_ended',**summary})
    if fatal:raise RuntimeError('Runner mechanism/authentication issue; inspect logs/runner_blocker.json')
    return results

def complete_phase(jobs,workers,phase):
    results=run_jobs(jobs,workers,phase)
    pendingkeys={(r['model'],r['key']) for r in results if r['state']=='pending_supplement'}
    pending=[j for j in jobs if (j['model'],j['key']) in pendingkeys]
    if pending and now()<DEADLINE:
        extra=run_jobs(pending,workers,phase+'_supplement',supplement=True)
        replacement={(r['model'],r['key']):r for r in extra}
        results=[replacement.get((r['model'],r['key']),r) for r in results]
    # User's later instruction extends network recovery until the deadline. The
    # original four + four attempts remain intact; each extra round has new logs.
    cycle=0
    while now()<DEADLINE:
        pendingkeys={(r['model'],r['key']) for r in results if network_recoverable(r) and not STATE.exhausted_model(r['model'])}
        if not pendingkeys:break
        cycle+=1
        for model in {m for m,_ in pendingkeys}:STATE.pause(model,120)
        pending=[j for j in jobs if (j['model'],j['key']) in pendingkeys]
        extra=run_jobs(pending,workers,phase+f'_network_{cycle:04d}',network_resume=True)
        replacement={(r['model'],r['key']):r for r in extra}
        results=[replacement.get((r['model'],r['key']),r) for r in results]
    return results

def finish_labels(results):
    items={r['id']:r for r in read_jsonl(ROOT/'data/processed/items.jsonl')};rows=[];counts=Counter()
    for result in results:
        ident=result['job']['item_id'];parsed=result.get('parsed') if result['state']=='valid' else None
        category=parsed['category'] if parsed else 'unclassified';quote=parsed['quote'] if parsed else ''
        rows.append({'id':ident,'category':category,'quote':quote,'quote_is_substring':quote in items[ident]['human_reasons'][0] if quote else False,
                     'state':result['state'],'human_reason':items[ident]['human_reasons'][0]});counts[category]+=1
    if len(rows)!=287 or any(r['state'] in ('deadline','quota_interrupted') for r in rows):
        save(ROOT/'labels/incomplete.json',{'expected':287,'obtained':len(rows),'counts':dict(counts)});return False
    from common import write_jsonl
    write_jsonl(ROOT/'labels/categories.jsonl',rows)
    choices=[(counts.get('C'+str(k),0),-k,k) for k in range(2,7)];winner=max(choices)
    k=winner[2] if winner[0] else None
    if k:ablation(k)
    save(ROOT/'labels/selection.json',{'k':k,'counts':dict(counts),'rule':'largest C2-C6; smallest index on tie','human_checked':False,'time':stamp()})
    gen=rng('spotcheck');picked=gen.choice(len(rows),20,replace=False)
    text='# 错误类型抽查（未经人工核对）\n\n'
    for index in picked:
        r=rows[int(index)];text+=f"## {r['id']}\n\n原文：{r['human_reason']}\n\n类别：{r['category']}\n\nquote：{r['quote']}\n\n作者核对：□\n\n"
    (ROOT/'labels/spotcheck_20.md').write_text(text,encoding='utf-8')
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['labels','pilot','main']);p.add_argument('--workers',type=int,default=4);p.add_argument('--batch',type=int,default=1);p.add_argument('--generation',type=int,default=0);p.add_argument('--model',choices=['terra','flash']);a=p.parse_args()
    if a.phase=='main' and (ROOT/'COLLECTION_FREEZE.json').exists():
        raise RuntimeError('Use the independently scheduled run_collection.py after split collection freeze')
    lock=SchedulerLock(ROOT/'logs/scheduler.lock');lock.__enter__()
    if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        if a.phase=='labels':
            results=complete_phase(labels_jobs(),a.workers,'labels')
            if not finish_labels(results):raise SystemExit('Labels incomplete: not frozen')
        elif a.phase=='pilot':
            assert (ROOT/'labels/selection.json').exists(),'Labels and k must be frozen before reviewing any test question'
            from common import sha
            frozen_labels=json.loads(subprocess.check_output(['git','show','labels-frozen:labels/final_audit.json'],cwd=ROOT,encoding='utf-8'))
            for relative,digest in frozen_labels['manifest'].items():assert sha(ROOT/relative)==digest,'Frozen label or ablation changed: '+relative
            from probes import probe_signature
            for model in ([a.model] if a.model else ['terra','flash']):
                probe=load(ROOT/'runs/probe/probe_report.json')['models'][model]
                assert probe['passed'] and probe['signature']==probe_signature(model),'Model probe has not passed for the current caller/configuration'
            jobs=pilot_jobs()
            if a.model:jobs=[j for j in jobs if j['model']==a.model]
            complete_phase(jobs,a.workers,'pilot_'+a.model if a.model else 'pilot')
        else:
            assert (ROOT/'FREEZE.md').exists(),'Cannot run main without freeze'
            from freeze import verify_frozen
            verify_frozen(a.generation)
            complete_phase(main_jobs(a.batch,a.generation),a.workers,f'main_g{a.generation}_b{a.batch}')
    finally:
        if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        lock.__exit__(None,None,None)

if __name__=='__main__':main()
