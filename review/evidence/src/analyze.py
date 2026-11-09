"""Analysis of complete, frozen batch prefixes. Never interprets Lean or revises labels."""
from __future__ import annotations
import argparse
import collections
import csv
import json
import os
import shutil
from pathlib import Path
import numpy as np
from common import ROOT,read_jsonl,load,save,rng,stamp
from statistics_core import item_rate,interval,compare,final_decision,fill_missing,auxiliary,mcnemar
from schedule import main_jobs
from experiment_runner import read_complete_jsonl
from telemetry import attempt_ledger,summarize_attempts
from reason_escape_reader import normalize_record,quality_for_jobs,RULE

CODES={'faithful':1,'unfaithful':0,'uncertain':2}

def read_results(stage):
    repair_enabled=(ROOT/'ANALYSIS_INPUT_AMENDMENT_01.json').exists()
    if stage.startswith('main/'):
        from collection_rules import analysis_allowed
        analysis_allowed(ROOT)
    records=[]
    for p in (ROOT/'runs'/stage).glob('*/*/result.json'):
        result=load(p)
        if repair_enabled and stage.startswith('main/'):result=normalize_record(result)
        result['_path']=str(p.relative_to(ROOT));records.append(result)
    return records

def complete_prefix(records,generation,model,require_quality=False):
    bykey={(r['model'],r['key']):r for r in records}
    prefixes=[]
    for batch in range(1,5):
        expected=[j for j in main_jobs(batch,generation) if j['model']==model]
        if not expected:break
        completed=all((model,j['key']) in bykey and bykey[(model,j['key'])]['state'] in ('valid','format_failure','tool_contaminated','final_missing') for j in expected)
        if not completed:break
        if require_quality:
            if (ROOT/'ANALYSIS_INPUT_AMENDMENT_01.json').exists():
                labels={r['id']:r['label'] for r in read_jsonl(ROOT/'data/processed/items.jsonl')}
                quality=quality_for_jobs(records,expected,labels)
                if not quality['passed']:break
                prefixes.append(batch);continue
            path=ROOT/'runs/main'/f'generation-{generation:02d}'/f'batch-{batch}-quality.json'
            if not path.exists():break
            quality=load(path)
            if not quality.get('models',{}).get(model,{}).get('passed',quality['passed']):break
        prefixes.append(batch)
    return prefixes

def summarize_votes(votes,labels,groups,gen,draws=10000):
    result={}
    for key,mask,kind in [('leak',~labels,'accept'),('reject',labels,'reject'),('uncertain_unfaithful',~labels,'uncertain'),('uncertain_faithful',labels,'uncertain'),('confirmed_unfaithful',~labels,'confirmed')]:
        values=item_rate(votes,kind);result[key]=interval(values[mask],groups[mask],draws,gen)
    for key,mask,kind in [('leak',~labels,'accept'),('reject',labels,'reject')]:
        bounds=[]
        for correct in [True,False]:bounds.append(float(np.mean(item_rate(fill_missing(votes,labels,correct),kind)[mask])) if mask.any() else None)
        result[key]['missing_best']=bounds[0];result[key]['missing_worst']=bounds[1]
    full=np.isfinite(votes).all(axis=1);aux=auxiliary(votes)
    majority=aux.pop('majority');allaccept=aux.pop('all_accept')
    for name,pred in [('majority',majority),('one_veto',allaccept)]:
        if pred is not None:
            validlabels=labels[full]
            aux[name]={'leak':float(np.mean(pred[~validlabels])) if (~validlabels).any() else None,
                       'reject':float(np.mean(1-pred[validlabels])) if validlabels.any() else None}
    result['auxiliary']=aux;result['total_votes']=int(votes.size);result['missing_votes']=int((~np.isfinite(votes)).sum())
    return result

def matrix(records,items,config,m):
    positions={r['id']:i for i,r in enumerate(items)};a=np.full((len(items),m),np.nan)
    for r in records:
        job=r['job']
        if job['config']!=config or job['item_id'] not in positions:continue
        if r['state']=='valid' and r.get('parsed'):
            rep=job['repetition']-1
            if rep<m:a[positions[job['item_id']],rep]=CODES[r['parsed']['verdict']]
    return a

def blocked_tool_sensitivity(records,items,m,labels,groups,generator,draws=10000):
    kept=[r for r in records if not r.get('blocked_evidence',False)]
    filtered={c:matrix(kept,items,c,m) for c in ['R0','R1','R1g']}
    return {'excluded_valid_calls':sum(r['state']=='valid' and bool(r.get('blocked_evidence')) for r in records),
            'comparisons':{x:compare(filtered['R1'],filtered[x],labels,groups,draws,generator) for x in ['R0','R1g']},
            'rule':'Exclude individual calls with confirmed blocked tool attempts; keep original published labels and remaining valid calls.'}

def unanimous_opposition(items,arrays,model_results):
    defined=all(model_results.get(model,{}).get('prefix') for model in ['terra','flash'])
    rows=[]
    if defined:
        for index,item in enumerate(items):
            observed=[];design=[];accidental=[]
            for model,matrices in arrays.items():
                prefix=model_results[model]['prefix']
                for config,votes in matrices.items():
                    if config in ('R0a','R0b') and item['label']=='true' and 4 not in prefix:
                        design.append({'model':model,'config':config,'reason':'faithful wording calls require batch 4'});continue
                    row=votes[index];missing=int((~np.isfinite(row)).sum())
                    if missing:accidental.append({'model':model,'config':config,'missing_votes':missing})
                    observed.extend(row[np.isfinite(row)].tolist())
            # Abstention is not an explicit statement opposing the published label.
            opposite=0 if item['label']=='true' else 1
            if observed and all(v==opposite for v in observed):
                rows.append({'id':item['id'],'label':item['label'],'complete':not design and not accidental,
                             'observed_valid_votes':len(observed),'missing_from_design':design,'missing_accidental':accidental,
                             'status':'未决（缺合格复核者）'})
    return {'defined':defined,'items':rows,'uncertain_counts_as_explicit_opposition':False,
            'scope':'Each model uses its complete analysis prefix; unrun faithful wording calls are listed as design omissions.'}

def planned_configs(model=None):
    configs=['R0','R1','R1g']+(['R1-k'] if (ROOT/'prompts/R1-k.txt').exists() else [])+['R0a','R0b']
    plan=ROOT/'COLLECTION_FREEZE.json'
    if model and plan.exists():configs=[c for c in configs if c in load(plan)['configs'][model]]
    return configs

def analyze_model(records,items,prefix,gen):
    if not prefix:return {'status':'incomplete_no_complete_batch','prefix':[]},{}
    records=[r for r in records if r['job']['batch'] in prefix]
    m=min(3,max(prefix));labels=np.array([r['label']=='true' for r in items]);groups=np.array([r['group'] for r in items])
    configs=planned_configs(records[0]['model'] if records else None)
    matrices={c:matrix(records,items,c,1 if c in ('R0a','R0b') else m) for c in configs}
    out={'status':'analyzed','prefix':prefix,'m':m,'configs':{},'comparisons':{},'sensitivity':{},'wording':{},'source_results':{},
         'state_counts':dict(collections.Counter(r['state'] for r in records))}
    for c,a in matrices.items():
        planned=(~labels) if c in ('R0a','R0b') and 4 not in prefix else np.ones(len(labels),bool)
        out['configs'][c]=summarize_votes(a[planned],labels[planned],groups[planned],gen)
        out['configs'][c]['not_run_by_design']=int((~planned).sum())
    spend=attempt_ledger()
    if records:
        stage=records[0]['job']['stage'];model=records[0]['model']
        lookup={r['key']:r['job']['config'] for r in records}
        for c,a in matrices.items():
            rows=[s for s in spend if s['model']==model and s['stage']==stage and lookup.get(s['key'])==c]
            accounting=summarize_attempts(rows);usage=accounting['known_usage']
            detected=int(np.any(a[~labels]==0,axis=1).sum());known_total=usage['input_tokens']+usage['output_tokens']
            out['configs'][c]['cost']={**accounting,'usage':usage,'attempts_without_usage':sum(not s.get('usage') for s in rows),
                'unique_unfaithful_items_explicitly_detected':detected,
                'recorded_tokens_per_unique_error_detected':known_total/detected if detected else None,
                'money_or_credits':'not converted unless an official rate is recorded; token counts are not credits'}
    for x in ['R0','R1g']:
        comp=compare(matrices['R1'],matrices[x],labels,groups,10000,gen)
        extremes={}
        for name,xcorrect,r1correct in [('x_worst_r1_best',False,True),('x_best_r1_worst',True,False)]:
            extremes[name]=compare(fill_missing(matrices['R1'],labels,r1correct),fill_missing(matrices[x],labels,xcorrect),labels,groups,10000,gen)
        comp['missing_extremes']=extremes
        comp['affected_by_missing']=len({comp['decision'],*(r['decision'] for r in extremes.values())})>1
        out['comparisons'][x]=comp
    out['decision']=final_decision(out['comparisons']['R0']['decision'],out['comparisons']['R1g']['decision'])
    for variant in ['R0a','R0b']:
        word=compare(matrices['R0'][:,:1],matrices[variant],labels,groups,10000,gen)
        for reference in ['R0','R1g']:
            diff=word['leak_diff'];ref=out['comparisons'][reference]['leak_diff']['estimate']
            word['same_scale_as_'+reference]=bool(diff['low'] is not None and (diff['low']>0 or diff['high']<0) and ref is not None and abs(diff['estimate'])>=abs(ref))
        out['wording'][variant]=word
    # Published-label sensitive subsets, never correcting the labels.
    for name,mask in [('exclude_known_issues',np.array([not r['known_issue'] for r in items])),('proofnet_only',np.array([r['source']=='proofnet' for r in items])),('exclude_uncertain',np.ones(len(items),bool))]:
        out['sensitivity'][name]={}
        for x in ['R0','R1g']:
            a=matrices['R1'][mask].copy();b=matrices[x][mask].copy()
            if name=='exclude_uncertain':a[a==2]=np.nan;b[b==2]=np.nan
            out['sensitivity'][name][x]=compare(a,b,labels[mask],groups[mask],10000,gen)
    out['sensitivity']['exclude_blocked_tools']=blocked_tool_sensitivity(records,items,m,labels,groups,gen)
    if m==3:
        out['sensitivity']['majority']={}
        for x in ['R0','R1g']:
            a=matrices['R1'];b=matrices[x];valid=np.isfinite(a).all(axis=1)&np.isfinite(b).all(axis=1)
            aa=((a[valid]==1).sum(axis=1)>=2).astype(float)[:,None];bb=((b[valid]==1).sum(axis=1)>=2).astype(float)[:,None]
            out['sensitivity']['majority'][x]=compare(aa,bb,labels[valid],groups[valid],10000,gen)
            out['sensitivity']['majority'][x]['mcnemar']=mcnemar(aa[:,0],bb[:,0])
    for source in ['minif2f','proofnet']:
        mask=np.array([r['source']==source for r in items]);out['source_results'][source]={}
        for c,a in matrices.items():
            planned=mask&((~labels) if c in ('R0a','R0b') and 4 not in prefix else True)
            out['source_results'][source][c]=summarize_votes(a[planned],labels[planned],groups[planned],gen)
    if (ROOT/'labels/categories.jsonl').exists():
        classes={r['id']:r['category'] for r in read_jsonl(ROOT/'labels/categories.jsonl')};out['error_types']={}
        for category in sorted(set(classes.values())):
            mask=np.array([classes.get(r['id'])==category for r in items])
            out['error_types'][category]={c:interval(item_rate(a)[mask],groups[mask],10000,gen) for c,a in matrices.items()}
    if 'R1-k' in matrices:
        out['ablation']=compare(matrices['R1'],matrices['R1-k'],labels,groups,10000,gen)
        out['ablation']['exploratory']=True
    primary={c:r['leak']['estimate'] for c,r in out['configs'].items() if c not in ('R0a','R0b') and r['leak']['estimate'] is not None}
    if primary:
        best=min(primary,key=primary.get);leak=out['configs'][best]['leak']['estimate'];reject=out['configs'][best]['reject']['estimate']
        base=float((~labels).mean());den=base*leak+(1-base)*(1-reject) if reject is not None else 0
        out['selected_best_description']={'config':best,'leak':out['configs'][best]['leak'],'accepted_error_fraction':float(base*leak/den) if den else None,'selection_bias_warning':True}
    return out,matrices

def main():
    p=argparse.ArgumentParser();p.add_argument('--generation',type=int,default=0);p.add_argument('--allow-unfrozen',action='store_true');a=p.parse_args()
    if not a.allow_unfrozen:
        from freeze import verify_frozen
        plan=verify_frozen(a.generation)
        os.environ['RC_BOOTSTRAP_METHOD']=plan['bootstrap_method']
        os.environ['RC_NONINFERIORITY_COVERAGE']=str(plan.get('noninferiority_coverage',.95))
    items=read_jsonl(ROOT/'data/processed/items.jsonl');records=read_results(f'main/generation-{a.generation:02d}')
    out={'generated':stamp(),'generation':a.generation,'counts':load(ROOT/'data/processed/counts.json'),'models':{},'exploratory_only_cross_model':True,
         'frozen_plan_verified':not a.allow_unfrozen}
    if (ROOT/'ANALYSIS_INPUT_AMENDMENT_01.json').exists():
        out['format_repair']={'rule':RULE,'decision_after_collection_started':True,
                             'raw_outputs_preserved':True,'amendment':'ANALYSIS_INPUT_AMENDMENT_01.md',
                             'by_model':{m:{'repaired_calls':sum(bool(r.get('format_repair')) for r in records if r['model']==m),
                                            'raw_states':dict(collections.Counter(r.get('format_repair',{}).get('original_state',r['state']) for r in records if r['model']==m))} for m in ['terra','flash']}}
    arrays={}
    for model in ['terra','flash']:
        subset=[r for r in records if r['model']==model];prefix=complete_prefix(records,a.generation,model,require_quality=not a.allow_unfrozen)
        # Reset the prescribed stream per model: one model's availability must not
        # change the other model's bootstrap draws or interval reproducibility.
        out['models'][model],arrays[model]=analyze_model(subset,items,prefix,rng('bootstrap'))
        out['models'][model]['all_observed_state_counts']=dict(collections.Counter(r['state'] for r in subset))
        partial=[r for r in subset if r['job']['batch'] not in prefix]
        out['models'][model]['outside_complete_prefix']={'calls':len(partial),'states':dict(collections.Counter(r['state'] for r in partial)),
            'blocked_attempt_calls':sum(bool(r.get('blocked_evidence')) for r in partial),'descriptive_only':True}
    save(ROOT/'analysis/main_results.json',out)
    columns=['model','config','metric','estimate','low','high','n','missing_best','missing_worst']
    with (ROOT/'analysis/main_table.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for model,result in out['models'].items():
            for config,metrics in result.get('configs',{}).items():
                for metric in ['leak','reject']:
                    row={'model':model,'config':config,'metric':metric,**metrics[metric]}
                    writer.writerow({key:row[key] for key in columns if key in row})
    save(ROOT/'analysis/unanimous_opposition.json',unanimous_opposition(items,arrays,out['models']))
    if any(r.get('configs') for r in out['models'].values()):
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
        if a.allow_unfrozen:fig.suptitle('Unfrozen diagnostic output - not formal results')
        for ax,(model,result) in zip(axes,out['models'].items()):
            configs=list(result.get('configs',{}));positions={config:i for i,config in enumerate(configs)}
            for j,metric in enumerate(['leak','reject']):
                entries=[(c,r[metric]) for c,r in result.get('configs',{}).items() if r[metric]['estimate'] is not None]
                if entries:
                    y=np.array([x[1]['estimate'] for x in entries])*100;lo=np.array([x[1]['low'] for x in entries])*100;hi=np.array([x[1]['high'] for x in entries])*100
                    x=np.array([positions[c] for c,_ in entries])+j*.12
                    ax.plot(x,y,'o',label=metric,color=f'C{j}');ax.vlines(x,lo,hi,color=f'C{j}')
            ax.set_xticks(range(len(configs)),configs);ax.set_title(model);ax.set_ylabel('Percent')
            if configs:ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2,frameon=False)
            else:ax.text(.5,.5,'No complete eligible batch',ha='center',va='center',transform=ax.transAxes)
        fig.savefig(ROOT/'analysis/main_rates.png',dpi=180);plt.close(fig)
    elif (ROOT/'analysis/main_rates.png').exists():
        # Preserve an earlier chart while preventing it from masquerading as the
        # current empty analysis. The historical generation copy is also retained.
        old=ROOT/'analysis/main_rates.png';destination=ROOT/'analysis'/('main_rates_previous_'+stamp().replace(':','-')+'.png')
        old.rename(destination)
    snapshot=ROOT/'analysis'/f'generation-{a.generation:02d}';snapshot.mkdir(exist_ok=True)
    for name in ['main_results.json','main_table.csv','unanimous_opposition.json','main_rates.png']:
        path=ROOT/'analysis'/name
        if path.exists():shutil.copyfile(path,snapshot/name)
    print('Analysis complete:',{m:r['status'] for m,r in out['models'].items()})

if __name__=='__main__':main()
