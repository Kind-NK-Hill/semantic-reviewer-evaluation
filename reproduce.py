"""Recompute frozen statistics offline; no model/network/Lean calls."""
import os
for variable in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[variable]='1'
import sys,json,argparse,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
from adapter import ROOT,load,read_jsonl
from analysis_core import analyze_model
from reason_escape_reader_source import repair_reason

def compare(a,b,path='root'):
    if isinstance(a,dict):
        for k,v in a.items():compare(v,b[k],path+'.'+k)
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'[{i}]')
    elif isinstance(a,(float,int)) and not isinstance(a,bool):
        assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(path,a,b)
    else:assert a==b,(path,a,b)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='recomputed');args=p.parse_args()
    settings=load(ROOT/'protocol/analysis_settings.json')
    os.environ['RC_BOOTSTRAP_METHOD']=settings['bootstrap_method']
    os.environ['RC_NONINFERIORITY_COVERAGE']=str(settings['noninferiority_coverage'])
    records=read_jsonl(ROOT/'data/judgments.jsonl');items=read_jsonl(ROOT/'data/processed/items.jsonl')
    assert len(records)==19170 and len({(r['model'],r['key']) for r in records})==19170
    repaired=0
    for r in records:
        if r['format_repair']:
            fixed=repair_reason(r['final_output']);assert fixed and fixed['parsed']==r['parsed'];repaired+=1
        elif r['state']=='valid':assert json.loads(r['final_output'])==r['parsed']
    assert repaired==114
    expected=load(ROOT/'results/main_results.json');plan=load(ROOT/'COLLECTION_FREEZE.json');out={}
    for model in ('terra','flash'):
        subset=[r for r in records if r['model']==model]
        assert len(subset)==plan['expected_calls'][model]
        out[model],_=analyze_model(subset,items,[1,2,3],np.random.default_rng(plan['seeds']['bootstrap']))
        compare(out[model],expected['models'][model])
        print(model,'matches frozen results',out[model]['decision']['action'])
    destination=ROOT/args.output;destination.mkdir(parents=True,exist_ok=True)
    (destination/'main_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Verified all frozen model statistics and114 deterministic repairs; no new calls.')

if __name__=='__main__':main()
