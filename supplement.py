"""Exploratory item-level diagnostics; do not alter the frozen decision tree."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
from adapter import ROOT,load,read_jsonl
from analysis_core import matrix
from statistics_core import interval

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='recomputed');args=p.parse_args()
    items=read_jsonl(ROOT/'data/processed/items.jsonl');records=read_jsonl(ROOT/'data/judgments.jsonl')
    labels=np.array([r['label']=='true' for r in items]);groups=np.array([r['group'] for r in items])
    gen=np.random.default_rng(20261109);os.environ['RC_BOOTSTRAP_METHOD']='percentile';os.environ['RC_NONINFERIORITY_COVERAGE']='0.95'
    arrays={m:{c:matrix([r for r in records if r['model']==m],items,c,3) for c in ('R0','R1','R1g')} for m in ('terra','flash')}
    out={'scope':'Exploratory post-collection diagnostics, not additional confirmatory claims','seed':20261109,'draws':10000,'intervals':'Item bootstrap95%; unadjusted for multiple comparisons','repeated':{},'transitions':{},'cross_model':{}}
    def metrics(pred,valid):
        return {name:interval((pred if name=='leak' else 1-pred)[valid&mask],groups[valid&mask],10000,gen) for name,mask in [('leak',~labels),('reject',labels)]}
    for model,configs in arrays.items():
        out['repeated'][model]={};out['transitions'][model]={}
        for c,a in configs.items():
            valid=np.isfinite(a).all(axis=1);accept=(a==1);false=valid&~labels;true=valid&labels
            policies={'first':accept[:,0].astype(float),'majority':(accept.sum(axis=1)>=2).astype(float),'all_three':accept.all(axis=1).astype(float)}
            out['repeated'][model][c]={'complete_items':int(valid.sum()),'unfaithful_items':int(false.sum()),'faithful_items':int(true.sum()),'all_three_accept_unfaithful':int((accept.all(axis=1)&false).sum()),'all_three_reject_faithful':int(((~accept).all(axis=1)&true).sum()),'false_accept_count_histogram':np.bincount(accept[false].sum(axis=1),minlength=4).tolist(),'policies':{p:metrics(v,valid) for p,v in policies.items()},'nominal_calls_per_item':{'first':1,'majority':3,'all_three':3}}
        for old,new in [('R0','R1'),('R1','R1g')]:
            a=configs[old];b=configs[new];valid=np.isfinite(a).all(axis=1)&np.isfinite(b).all(axis=1)
            aa=(a==1).sum(axis=1)>=2;bb=(b==1).sum(axis=1)>=2
            rows={}
            for src in ('all','minif2f','proofnet'):
                v=valid if src=='all' else valid&np.array([r['source']==src for r in items])
                f=v&~labels;t=v&labels
                rows[src]={'leaks_removed':int((aa&~bb&f).sum()),'leaks_introduced':int((~aa&bb&f).sum()),'rejections_removed':int((~aa&bb&t).sum()),'rejections_introduced':int((aa&~bb&t).sum())}
            out['transitions'][model][old+'->'+new]={'rule':'Majority of3; uncertain counts as nonacceptance','by_source':rows}
    for c in ('R1','R1g'):
        a=arrays['terra'][c][:,0];b=arrays['flash'][c][:,0];valid=np.isfinite(a)&np.isfinite(b);false=valid&~labels
        cells={f'{x},{y}':int(((a==x)&(b==y)&false).sum()) for x in (0,1,2) for y in (0,1,2)}
        out['cross_model'][c]={'rule':'Fixed first repetition, same858items; second opinion is an offline replay, not a deployed multi-agent workflow','unfaithful_cells_terra_flash':cells,'codes':{'0':'explicitly unfaithful','1':'faithful','2':'uncertain'},'policies':{name:metrics(pred,valid) for name,pred in {'terra_only':(a==1).astype(float),'flash_only':(b==1).astype(float),'both_accept':((a==1)&(b==1)).astype(float)}.items()},'extra_explicit_detections_after_terra_accept':int(((a==1)&(b==0)&false).sum()),'extra_explicit_detections_after_flash_accept':int(((b==1)&(a==0)&false).sum()),'both_accept_unfaithful':int(((a==1)&(b==1)&false).sum())}
    destination=ROOT/args.output;destination.mkdir(parents=True,exist_ok=True)
    (destination/'supplement.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Exploratory diagnostics written:',destination/'supplement.json')

if __name__=='__main__':main()
