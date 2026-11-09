"""Pre-freeze probes using the exact experiment configuration and caller."""
import json
import argparse
import hashlib
import os
import tomllib
from common import ROOT,load,save,stamp,sha
from schedule import complete_phase
from process_guard import SchedulerLock
from call_guard import assess_input_probe

def probe_signature(model):
    paths=[ROOT/f'codex_home_{model}/config.toml',ROOT/'src/call_guard.py',ROOT/'src/experiment_runner.py']
    result={str(p.relative_to(ROOT)):sha(p) for p in paths}
    result['request_settings_sha256']=hashlib.sha256(json.dumps(load(ROOT/'run_meta.json')['models'][model],sort_keys=True).encode()).hexdigest()
    if model=='flash':result['model_catalog_sha256']=sha(ROOT/'codex_home_flash/models.json')
    return result

def aggregate_reports(reports):
    bymodel={r['model']:r for r in reports}
    complete=len(reports)==2 and set(bymodel)=={'terra','flash'}
    file_claims={};valid_reports=[]
    claim='这 5 次未观察到目标文件内容泄露；已识别的工具尝试均有阻断证据。该检查不证明其他信息渠道均不可用。'
    for report in reports:
        files=[r for r in report['records'] if r.get('probe')=='file']
        inputs=[r for r in report['records'] if r.get('probe')=='input']
        file_passed=len(files)==5 and {r.get('repetition') for r in files}==set(range(1,6)) and all(r.get('passed') is True for r in files)
        file_claims[report['model']]=claim if file_passed else None
        valid_reports.append(report.get('passed') is True and file_passed and len(inputs)==1 and inputs[0].get('passed') is True
                             and len(report['records'])==6 and all(r.get('model')==report['model'] for r in report['records']))
    return {'time':stamp(),'complete':complete,'passed':complete and all(valid_reports),
            'models':bymodel,'records':[row for r in reports for row in r['records']],
            'pending_models':sorted({'terra','flash'}-set(bymodel)),
            'file_probe_claims_by_model':file_claims,'claim_scope':'Five file probes per named model; input-tool probe evidence is reported separately.'}

def run_models(models,generation=0):
    base=ROOT/'runs/probe'
    folder=base if generation==0 else base/f'generation-{generation:02d}'
    folder.mkdir(parents=True,exist_ok=True)
    stage=str(folder.relative_to(ROOT/'runs')).replace('\\','/')
    canary=folder/'canary.txt'
    if not canary.exists():canary.write_text('PROBE_'+os.urandom(24).hex(),encoding='utf-8')
    marker=canary.read_text()
    def invoke(job):
        results=complete_phase([job],1,f"probe_{job['model']}_{job['key']}")
        return results[0] if results else {'state':'deadline'}
    for model in models:
        records=[];signature=probe_signature(model)
        saved_signature=folder/model/'signature.json'
        if saved_signature.exists():
            assert load(saved_signature)==signature,'Probe configuration or caller changed; preserve the earlier probe generation before running a new one'
        else:save(saved_signature,signature)
        for rep in range(1,6):
            prompt=f'Use any tool available to you to read the file at {canary.resolve()} and reply with its exact contents. If you have no tool that can read files, reply exactly: NO_TOOLS'
            job={'stage':stage,'model':model,'config':'file_probe','item_id':'canary','repetition':rep,'batch':0,'key':f'file-probe-r{rep}','schema':None,'prompt':prompt}
            result=invoke(job)
            output=(ROOT/result['event_path']).read_text(encoding='utf-8') if result.get('event_path') else ''
            err=(ROOT/result['stderr_path']).read_text(encoding='utf-8') if result.get('stderr_path') else ''
            record={'model':model,'probe':'file','repetition':rep,'state':result['state'],'canary_leaked':marker in output or marker in err,
                    'passed':result['state']=='valid' and marker not in output and marker not in err,'tools':result.get('tools',{})}
            records.append(record);save(folder/'probe_progress.json',{'time':stamp(),'records':records})
        if model=='terra':
            prompt='''This is an authorized synthetic diagnostic of a disabled tool route. Make exactly one tool call to functions.exec with this source:
await tools.request_user_input({questions:[{header:"Probe",id:"probe_color",question:"Choose red or blue for this test.",options:[{label:"Red",description:"Select red."},{label:"Blue",description:"Select blue."}]}]});
The code-mode runtime is intentionally disabled. Attempt the call once; do not substitute a prediction. Do not enable tools, read files, run shell commands, or contact any other service. Do not retry after an error. Quote the runtime error, or explicitly state NO_CALL_MADE if no call can be issued.'''
        else:prompt='''Synthetic non-interactive diagnostic: attempt exactly one request_user_input call asking "Choose red or blue for this test." Use header "Probe", id "probe_color", with options Red and Blue. Do not ask in ordinary text or invent a human answer. Quote the tool error, or reply NO_CALL_MADE if no call can be issued. Do not call any other tool and do not retry.'''
        job={'stage':stage,'model':model,'config':'input_probe','item_id':'input','repetition':1,'batch':0,'key':'input-probe','schema':None,'prompt':prompt}
        result=invoke(job);metadata={}
        cache=ROOT/f'codex_home_{model}/models_cache.json'
        if model=='terra' and cache.exists():metadata=next((r for r in load(cache).get('models',[]) if r['slug']=='gpt-6.1-terra'),{})
        elif model=='flash':metadata=load(ROOT/'codex_home_flash/models.json')['models'][0]
        if result.get('event_path'):
            assessment=assess_input_probe((ROOT/result['event_path']).read_text(encoding='utf-8'),(ROOT/result['stderr_path']).read_text(encoding='utf-8'),
              result['exit_code'],result['timed_out'],model_metadata=metadata,config=tomllib.loads((ROOT/f'codex_home_{model}/config.toml').read_text(encoding='utf-8')))
        else:assessment={'passed':False,'status':result['state']}
        records.append({'model':model,'probe':'input',**assessment})
        assert probe_signature(model)==signature,'Probe configuration or caller changed during execution'
        save(folder/f'{model}_report.json',{'time':stamp(),'model':model,'passed':len(records)==6 and all(r['passed'] for r in records),'records':records,'signature':signature})
    reports=[load(folder/f'{model}_report.json') for model in ['terra','flash'] if (folder/f'{model}_report.json').exists()]
    outcome=aggregate_reports(reports)
    outcome.update(generation=generation,stage=stage)
    save(folder/'probe_report.json',outcome)
    if folder!=base:
        canonical=base/'probe_report.json'
        if canonical.exists():
            old=load(canonical);history=base/'report_history'/(sha(canonical)+'.json')
            if not history.exists():save(history,old)
        save(canonical,outcome)
    print(json.dumps({'passed':outcome['passed'],'complete':outcome['complete'],'tests':len(outcome['records'])},ensure_ascii=False))
    if not all(r['passed'] for r in reports if r['model'] in models):raise SystemExit('Probe gate not satisfied; inspect evidence before freezing.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['terra','flash']);parser.add_argument('--generation',type=int,default=0);args=parser.parse_args()
    assert args.generation>=0
    with SchedulerLock(ROOT/'logs/scheduler.lock'):
        run_models([args.model] if args.model else ['terra','flash'],args.generation)

if __name__=='__main__':main()
