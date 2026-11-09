"""Exploratory item-level diagnostics; do not alter the frozen decision tree."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
import numpy as np
from adapter import ROOT,load,read_jsonl
from analysis_core import matrix
from statistics_core import interval,compare,final_decision,item_rate

def review_additions(items,records,arrays):
    """Post-review descriptive replay; leave frozen comparisons/labels untouched."""
    labels=np.array([r['label']=='true' for r in items]);groups=np.array([r['group'] for r in items])
    ledger=load(ROOT/'data/attempt_ledger.json')
    rates={'terra':{'uncached_input':25,'cached_input':1.25,'output':125,'unit':'credits'},
           'flash':{'uncached_input':1,'cached_input':.02,'output':4,'unit':'CNY'}}
    strategies=[('terra_R1_first',[('terra','R1',[1])]),('terra_R1_all3',[('terra','R1',[1,2,3])]),
                ('terra_R1g_first',[('terra','R1g',[1])]),('flash_R1g_first',[('flash','R1g',[1])]),
                ('flash_R1g_all3',[('flash','R1g',[1,2,3])]),('both_R1_first',[('terra','R1',[1]),('flash','R1',[1])]),
                ('both_R1g_first',[('terra','R1g',[1]),('flash','R1g',[1])])]
    rows={}
    for name,components in strategies:
        votes=np.column_stack([arrays[m][c][:,np.array(reps)-1] for m,c,reps in components])
        valid=np.isfinite(votes).all(axis=1);accepted=(votes==1).all(axis=1)
        chosen={(r['model'],r['key']) for r in records if any(r['model']==m and r['job']['config']==c and r['job']['repetition'] in reps for m,c,reps in components)}
        cost={}
        for model in sorted({m for m,_,_ in components}):
            attempts=[r for r in ledger if (r['model'],r['key']) in chosen and r['model']==model]
            fields=('input_tokens','cached_input_tokens','output_tokens')
            usage={k:sum(r['usage'].get(k,0) for r in attempts) for k in fields}
            rate=rates[model];known=((usage['input_tokens']-usage['cached_input_tokens'])*rate['uncached_input']+usage['cached_input_tokens']*rate['cached_input']+usage['output_tokens']*rate['output'])/1e6
            cost[model]={'selected_attempts':len(attempts),'distinct_calls':len({r['key'] for r in attempts}),
                         'known_usage':usage,'estimated_observed_cost':known,'unit':rate['unit'],
                         'attempts_with_unknown_charge':sum(bool(r['possible_charge_unknown']) for r in attempts)}
        rows[name]={'components':[{'model':m,'config':c,'repetitions':reps} for m,c,reps in components],
                    'complete_items':int(valid.sum()),'unfaithful_items':int((valid&~labels).sum()),'faithful_items':int((valid&labels).sum()),
                    'false_accept_items':int((valid&~labels&accepted).sum()),'false_reject_items':int((valid&labels&~accepted).sum()),
                    'false_accept_rate':float(accepted[valid&~labels].mean()),'false_reject_rate':float((~accepted[valid&labels]).mean()),
                    'nominal_calls_per_item':sum(len(reps) for _,_,reps in components),'selected_calls':len(chosen),'cost_by_provider':cost}
        assert rows[name]['complete_items']==858
        assert rows[name]['selected_calls']==858*rows[name]['nominal_calls_per_item']
    base=[r for r in records if r['model']=='flash'];raw=[{**r,'state':r['raw_state']} for r in base]
    raw_view={c:matrix(raw,items,c,3) for c in ('R0','R1','R1g')}
    raw_block={c:{'invalid_votes':int(np.isnan(a).sum()),'false_reject_rate':float((a[labels]!=1).mean()),'false_accept_rate':float((a[~labels]==1).mean())} for c,a in raw_view.items()}
    old_coverage=os.environ.get('RC_NONINFERIORITY_COVERAGE','0.95');os.environ['RC_NONINFERIORITY_COVERAGE']='0.975'
    comparisons={}
    for c in ('R0','R1g'):
        comparisons[c]=compare(raw_view['R1'],raw_view[c],labels,groups,10000,np.random.default_rng(load(ROOT/'COLLECTION_FREEZE.json')['seeds']['bootstrap']))
    os.environ['RC_NONINFERIORITY_COVERAGE']=old_coverage
    counts={};labels_by_id={r['id']:r['label'] for r in items}
    for r in raw:
        job=r['job'];label=labels_by_id[job['item_id']]
        key=(job['batch'],job['config'],label);v=counts.setdefault(key,{'total':0,'bad':0})
        v['total']+=1;v['bad']+=r['state']!='valid'
    violations=[{'batch':b,'config':c,'label':label,**v} for (b,c,label),v in sorted(counts.items()) if v['bad']/v['total']>.02]
    direct={};direct_gen=np.random.default_rng(20261110)
    for name,mask,kind in [('leak_diff',~labels,'accept'),('reject_diff',labels,'reject')]:
        delta=item_rate(arrays['terra']['R1g'],kind)-item_rate(arrays['terra']['R0'],kind)
        direct[name]=interval(delta[mask],groups[mask],10000,direct_gen)
    direct.update(direction='R1g minus R0',scope='Exploratory direct Terra comparison of three-repetition item means; no new selection decision',seed=20261110,draws=10000)
    direct['sample_weighted_error_tradeoff']={'unfaithful_items':288,'faithful_items':570,
        'mean_false_accept_change_per_858_items':direct['leak_diff']['estimate']*288,
        'mean_false_reject_change_per_858_items':direct['reject_diff']['estimate']*570,
        'break_even_false_accept_cost_over_false_reject_cost':(direct['reject_diff']['estimate']*570)/(-direct['leak_diff']['estimate']*288),
        'assumptions':'Same item composition; linear per-error costs; ignore model-call/latency/manual-review costs. Hypothetical point-estimate tradeoff, not measured business utility.'}
    return {'scope':'Post-review diagnostics; no new model calls, no relabeling and no frozen decision changes',
            'rates_per_million_at_collection':rates,'cost_scope':'Exactly the stored attempts belonging to each replayed policy; not the cost of prospectively deploying it. Cached context and retry history are retained. Missing usage is unknown charge. Provider currencies are not added together.',
            'strategies':rows,'terra_R1g_minus_R0':direct,'raw_invalid_as_blocked':{'model':'flash','rule':'Every raw invalid final vote counts as not accepted; denominator includes all planned votes','configs':raw_block},
            'strict_raw_missing_sensitivity':{'model':'flash','comparisons':comparisons,'decision':final_decision(comparisons['R0']['decision'],comparisons['R1g']['decision']),
                'raw_quality_violations':violations,'passes_original_quality_gate':not violations,
                'scope':'Numerical sensitivity using remaining raw-valid votes only; does not make raw-only collection eligible under the original2% gate.'}}

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
    out['review_additions']=review_additions(items,records,arrays)
    destination=ROOT/args.output;destination.mkdir(parents=True,exist_ok=True)
    (destination/'supplement.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Exploratory diagnostics written:',destination/'supplement.json')

if __name__=='__main__':main()
