"""Independent providers; blinded monitoring; no automatic analysis or case inspection."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
import os
import threading
import time
from common import ROOT,load,save,stamp,now,DEADLINE,read_jsonl,sha
from process_guard import SchedulerLock,identity,still_alive
from split_freeze import verify_collection
from schedule import main_jobs,complete_phase
from experiment_runner import STATE
from collection_rules import admission_delay

QUALITY_LOCK=threading.Lock()

def store_quality(model,batch,results):
    labels={x['id']:x['label'] for x in read_jsonl(ROOT/'data/processed/items.jsonl')}
    groups=defaultdict(Counter)
    terminal={'valid','format_failure','tool_contaminated','final_missing'}
    for row in results:
        if row['state'] not in terminal:continue
        key=(row['job']['config'],labels[row['job']['item_id']]);groups[key]['total']+=1
        if row['state']!='valid':groups[key]['bad']+=1
    violations=[{'model':model,'config':c,'label':l,**dict(v)} for (c,l),v in groups.items() if v['bad']/v['total']>.02]
    complete=all(x['state'] in terminal for x in results)
    path=ROOT/'runs/main/generation-00'/f'batch-{batch}-quality.json'
    with QUALITY_LOCK:
        record=load(path) if path.exists() else {'models':{},'violations':[]}
        if path.exists():
            history=path.parent/'quality_history'/f'batch-{batch}-{sha(path)}.json'
            if not history.exists():save(history,record)
        record['models'][model]={'passed':complete and not violations,'complete':complete}
        record['violations']=[v for v in record['violations'] if v['model']!=model]+violations
        record.update(time=stamp(),passed=all(x.get('passed',False) for x in record['models'].values()))
        save(path,record)
    return violations,complete

def quality_action(plan,results,violations,complete,normalized_quality=None):
    if not violations:return 'continue' if complete else 'incomplete'
    if (complete and plan.get('approved_reason_escape_quality') is True
            and normalized_quality and normalized_quality['passed']
            and normalized_quality['repaired_calls']>0):
        return 'continue_after_approved_format_repair'
    if complete and plan.get('continue_format_failures') is True and all(r['state'] in ('valid','format_failure') for r in results):
        return 'continue_with_failed_quality_record'
    return 'stop_this_model'

def worker(model,plan):
    path=ROOT/'logs'/f'collection_{model}.json'
    def status(state,**extra):save(path,{'time':stamp(),'process':identity(os.getpid()),'model':model,'state':state,**extra})
    status('waiting_startup_validation')
    previous=plan.get('startup_wait_processes',{}).get(model)
    while previous and still_alive(previous) and now()<DEADLINE:
        status('waiting_existing_probe',probe_process=previous);time.sleep(5)
    exhausted=ROOT/'logs/model_exhausted.json'
    if exhausted.exists() and model in load(exhausted)['models']:
        STATE.exhaust(model);status('quota_exhausted');return
    while admission_delay(model)>0 and now()<DEADLINE:
        if (ROOT/'logs/collection_stop.json').exists():status('stopped_for_repair');return
        status('waiting_offpeak',seconds_to_admission=admission_delay(model));time.sleep(min(30,admission_delay(model)))
    if now()>=DEADLINE:status('deadline');return
    from probes import probe_signature,run_models
    probe=ROOT/f"runs/probe/generation-{plan['startup_probe_generation']:02d}/{model}_report.json"
    if not probe.exists() or not load(probe)['passed'] or load(probe)['signature']!=probe_signature(model):
        status('startup_probes');run_models([model],plan['startup_probe_generation'])
    assert load(probe)['passed'] and load(probe)['signature']==probe_signature(model)
    for batch in plan['batches'][model]:
        if now()>=DEADLINE or STATE.exhausted_model(model):break
        verify_collection();status('collecting',batch=batch)
        jobs=[j for j in main_jobs(batch,0) if j['model']==model]
        results=complete_phase(jobs,plan['workers'][model],f'collection_{model}_b{batch}')
        assert len(results)==len(jobs),'Incomplete scheduler accounting'
        violations,complete=store_quality(model,batch,results)
        counts=dict(Counter(x['state'] for x in results))
        if violations:
            normalized_quality=None
            if plan.get('approved_reason_escape_quality') is True:
                from split_freeze import verify_analysis
                from reason_escape_reader import normalize_record,quality_for_jobs
                verify_analysis()
                assert (ROOT/'ANALYSIS_INPUT_AMENDMENT_01.json').exists()
                labels={x['id']:x['label'] for x in read_jsonl(ROOT/'data/processed/items.jsonl')}
                normalized_quality=quality_for_jobs([normalize_record(r) for r in results],jobs,labels)
            action=quality_action(plan,results,violations,complete,normalized_quality)
            quality_path=ROOT/'logs'/f'collection_quality_{model}_b{batch}.json'
            if quality_path.exists():
                history=ROOT/'logs/quality_history'/f'{quality_path.stem}-{sha(quality_path)}.json'
                if not history.exists():save(history,load(quality_path))
            save(quality_path,{'time':stamp(),'generation':0,'model':model,'batch':batch,'violations':violations,'action':action,'analysis_quality_passed':False,'normalized_quality':normalized_quality})
            if action=='stop_this_model':status('quality_repair_required',batch=batch,counts=counts);return
            status('continuing_with_recorded_format_failures',batch=batch,counts=counts)
        status('batch_finished',batch=batch,counts=counts,complete=complete)
        if not complete:status('collection_incomplete',batch=batch,counts=counts);return
    status('deadline' if now()>=DEADLINE else 'quota_exhausted' if STATE.exhausted_model(model) else 'collection_finished_analysis_not_run')

def main():
    plan=verify_collection();assert plan['auto_analysis'] is False
    assert not (ROOT/'logs/collection_stop.json').exists(),'Repair requires a new audited generation'
    with SchedulerLock(ROOT/'logs/supervisor.lock'),SchedulerLock(ROOT/'logs/collection_scheduler.lock'):
        from hardware_guard import GOVERNOR
        GOVERNOR.configure_terra(plan['workers']['terra'])
        if os.name=='nt':
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures={pool.submit(worker,m,plan):m for m in ['terra','flash']}
                for f in as_completed(futures):
                    try:f.result()
                    except Exception as exc:
                        save(ROOT/'logs/collection_stop.json',{'time':stamp(),'generation':0,'model':futures[f],'error':type(exc).__name__+': '+str(exc)})
                        raise
        finally:
            save(ROOT/'logs/collection_supervisor.json',{'time':stamp(),'automatic_analysis_invoked':False,'process':identity(os.getpid()),'state':'ended'})
            if os.name=='nt':ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)

if __name__=='__main__':main()
