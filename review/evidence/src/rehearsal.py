import argparse
import json
import time
import os
import numpy as np
from scipy.stats import norm
from common import ROOT,save,load,read_jsonl,rng,seed,stamp
from statistics_core import item_rate,compare,final_decision,bootstrap_distribution,power,pair_decision,fill_missing,auxiliary

def deterministic():
    items=read_jsonl(ROOT/'data/processed/items.jsonl');labels=np.array([r['label']=='true' for r in items]);groups=np.array([r['group'] for r in items]);gen=rng('simulation')
    n=len(items);truth=np.tile(labels[:,None],(1,3)).astype(float)
    results=[]
    for name,votes,leak,reject in [('always_faithful',np.ones((n,3)),1,0),('always_unfaithful',np.zeros((n,3)),0,1),('perfect',truth,0,0)]:
        got=(float(item_rate(votes)[~labels].mean()),float(item_rate(votes,'reject')[labels].mean()));assert got==(leak,reject)
        results.append({'name':name,'leak':got[0],'reject':got[1],'pass':True})
    identical=compare(truth,truth,labels,groups,2000,gen);assert identical['decision']=='x_noninferior'
    r0=truth.copy();r1=truth.copy();idx=gen.choice(np.flatnonzero(~labels),29,replace=False);r0[idx,:]=1
    better=compare(r1,r0,labels,groups,2000,gen);assert better['decision']=='r1_superior'
    uncertain=r0.copy();uncertain[idx,:]=2
    abstention=compare(uncertain,r0,labels,groups,2000,gen);assert abstention['decision']=='more_rejection_or_abstention'
    missing=r0.copy();missing[np.flatnonzero(~labels)[:17],:]=np.nan
    bounds=[float(item_rate(fill_missing(missing,labels,c))[~labels].mean()) for c in [True,False]];assert bounds[0]<=bounds[1]
    a=auxiliary(np.array([[1,0,2],[1,1,np.nan],[np.nan,np.nan,np.nan]]));assert a['n_complete']==1 and a['majority'].tolist()==[0]
    edge={'leak_diff':{'low':0,'high':.05},'reject_diff':{'low':0,'high':.05},'confirmed_diff':{'low':0,'high':0}}
    assert pair_decision(edge)=='insufficient'
    assert final_decision('r1_superior','x_noninferior')['action']=='replace_with_r1g'
    assert final_decision('more_rejection_or_abstention','r1_superior')['rationale']=='insufficient_against_r0'
    # Same exact sufficient-statistics bootstrap as explicit index sampling in distribution.
    values=np.array([0.,0.,1.,1.]);dist=bootstrap_distribution(values,np.arange(4),100000,np.random.default_rng(17))[:,0]
    assert abs(np.mean(dist)-.5)<.005 and abs(np.var(dist)-.0625)<.003
    assert .04<power(3,.2,0)['minimum_detectable_difference']<.05
    assert .34<power(3,.3,1)['noninferiority_probability_if_equal']<.35
    return {'passed':True,'cases':results,'identical':identical,'improvement':better,'abstention':abstention,'missing_bounds':bounds,'boot_equivalence_checked':True}

def simulate(scenario,sc,sr,m,iterations=1000,draws=2000,master_seed=None):
    # Seeds are reproducibly derived from the prescribed simulation seed, independent of scheduling.
    tag=f'{scenario}:{sc}:{sr}:{m}'
    import hashlib
    base=seed('simulation') if master_seed is None else int(hashlib.sha256((str(master_seed)+':simulation').encode()).hexdigest()[:8],16)
    derived=int(hashlib.sha256((str(base)+':'+tag).encode()).hexdigest()[:16],16)
    gen=np.random.default_rng(derived)
    labels=np.array([False]*288+[True]*570);groups=np.arange(858)
    configs=3 if scenario=='S3' else 2
    rates=np.full((configs,2),[.30,.85]) # acceptance probability by published label.
    if scenario=='S1':rates[1,0]=.35
    if scenario=='S2':rates[0,0]=.20
    intercept=norm.ppf(rates)*np.sqrt(1+sc*sc+sr*sr)
    covered=wrong_superior=wrong_noninferior=detected=tree_error=0
    qs=[];rhos=[]
    truth_difference=float(rates[1,0]-rates[0,0])
    for iteration in range(iterations):
        u=gen.standard_normal((858,1,1));v=gen.standard_normal((858,configs,1));e=gen.standard_normal((858,configs,m))
        z=intercept[:,labels.astype(int)].T[:,:,None]+u+sc*v+sr*e
        votes=(z>0).astype(float)
        # Deterministic fraction per configuration; random fixed-size allocation among rejections.
        for c in range(configs):
            rejected=np.flatnonzero(votes[:,c,:].ravel()==0)
            chosen=gen.choice(rejected,int(round(.2*len(rejected))),replace=False)
            flat=votes[:,c,:].copy().ravel();flat[chosen]=2;votes[:,c,:]=flat.reshape(858,m)
        comp=compare(votes[:,0,:],votes[:,1,:],labels,groups,draws,gen)
        ci=comp['leak_diff'];covered+=ci['low']<=truth_difference<=ci['high']
        wrong_superior+=comp['decision']=='r1_superior';wrong_noninferior+=comp['decision']=='x_noninferior';detected+=comp['decision']=='r1_superior'
        if scenario=='S3':
            other=compare(votes[:,0,:],votes[:,2,:],labels,groups,draws,gen)
            decision=final_decision(comp['decision'],other['decision']);tree_error+=decision['claims_superiority']
        diff=(votes[:288,1,:]==1).astype(float)-(votes[:288,0,:]==1).astype(float)
        qs.append(float(np.mean(diff!=0)))
        if m>1:
            corrs=[]
            for a in range(m):
                for b in range(a+1,m):
                    if np.std(diff[:,a])>0 and np.std(diff[:,b])>0:corrs.append(float(np.corrcoef(diff[:,a],diff[:,b])[0,1]))
            if corrs:rhos.append(float(np.mean(corrs)))
    result={'scenario':scenario,'sc':sc,'sr':sr,'m':m,'iterations':iterations,'bootstrap_draws':draws,
            'coverage':covered/iterations,'superior_rate':wrong_superior/iterations,'noninferior_rate':wrong_noninferior/iterations,
            'tree_superiority_rate':tree_error/iterations if scenario=='S3' else None,'mean_q':float(np.mean(qs)),'mean_rho':float(np.mean(rhos)) if rhos else None,
            'derived_seed':derived}
    if scenario=='S0':passed=.93<=result['coverage']<=.97 and result['superior_rate']<=.04
    elif scenario=='S1':passed=result['noninferior_rate']<=.04
    elif scenario=='S3':passed=result['tree_superiority_rate']<=.04
    else:passed=True
    result['passed']=bool(passed)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);parser.add_argument('--deterministic-only',action='store_true');parser.add_argument('--candidate',choices=['bca','studentized']);args=parser.parse_args()
    prefix='rehearsal'
    if args.candidate:
        os.environ['RC_BOOTSTRAP_METHOD']=args.candidate
        prefix='rehearsal_candidate_'+args.candidate
    d=deterministic();save(ROOT/'analysis'/f'{prefix}_deterministic.json',d)
    if args.deterministic_only:print('Deterministic rehearsal passed.');return
    from concurrent.futures import ProcessPoolExecutor,as_completed
    cases=[(s,sc,sr,m) for s in ['S0','S1','S2','S3'] for sc,sr,ms in [(.8,0,[3]),(.5,.5,[1,2,3]),(0,.8,[3])] for m in ms]
    results=[];began=time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(simulate,*case):case for case in cases}
        for future in as_completed(futures):
            result=future.result();results.append(result)
            save(ROOT/'analysis'/f'{prefix}_simulation_progress.json',{'updated':stamp(),'finished':len(results),'total':len(cases),'results':results})
            print(json.dumps(result),flush=True)
    outcome={'passed':all(r['passed'] for r in results),'elapsed_seconds':time.time()-began,'deterministic':d,'simulation':sorted(results,key=lambda r:(r['scenario'],r['sc'],r['m']))}
    outcome['bootstrap_method']=args.candidate or 'percentile';outcome['candidate_only']=bool(args.candidate)
    save(ROOT/'analysis'/f'{prefix}.json',outcome)
    md='# 假数据彩排\n\n确定性检查通过。模拟严格沿用任务单固定场景、每场景组合 1,000 次和每次 2,000 次 bootstrap。\n\n|场景|s_c|s_r|m|覆盖率|显著更好率|不差于率|完整判定树错误率|通过|\n|---|---:|---:|---:|---:|---:|---:|---:|---|\n'
    for r in outcome['simulation']:md+=f"|{r['scenario']}|{r['sc']}|{r['sr']}|{r['m']}|{r['coverage']}|{r['superior_rate']}|{r['noninferior_rate']}|{r['tree_superiority_rate']}|{r['passed']}|\n"
    (ROOT/'analysis'/f'{prefix}.md').write_text(md,encoding='utf-8')
    if not outcome['passed']:raise SystemExit('Simulation gate failed; diagnose before freezing, do not relax thresholds.')

if __name__=='__main__':main()
