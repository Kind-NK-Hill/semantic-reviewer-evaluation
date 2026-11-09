"""Author-prespecified independent confirmation; no model records are read."""
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from scipy.stats import binomtest
from common import ROOT, save, load, stamp, sha
from rehearsal import simulate

def main():
    output=ROOT/'analysis/confirmation_20261109.json'
    assert not output.exists(),'Never overwrite a confirmation result'
    os.environ['RC_BOOTSTRAP_METHOD']='percentile'
    os.environ['RC_NONINFERIORITY_COVERAGE']='0.975'
    os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
    paths=['src/statistics_core.py','src/rehearsal.py','src/confirm_analysis.py']
    hashes={p:sha(ROOT/p) for p in paths}
    cases=[(s,sc,sr,m) for s in ['S0','S1','S3'] for sc,sr,ms in [(.8,0,[3]),(.5,.5,[1,2,3]),(0,.8,[3])] for m in ms]
    rows=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(simulate,*case,master_seed=20261109) for case in cases]
        for f in as_completed(futures):
            row=f.result();row['binomial_intervals']={}
            for field in ['coverage','superior_rate','noninferior_rate','tree_superiority_rate']:
                if row[field] is None:continue
                count=round(row[field]*1000);ci=binomtest(count,1000).proportion_ci(confidence_level=.95,method='exact')
                row['binomial_intervals'][field]={'events':count,'n':1000,'estimate':count/1000,'low':ci.low,'high':ci.high}
            rows.append(row)
            save(ROOT/'analysis/confirmation_progress.json',{'time':stamp(),'done':len(rows),'planned':15,'results':rows})
            print({'done':len(rows),'scenario':row['scenario'],'passed':row['passed']},flush=True)
    assert all(sha(ROOT/p)==h for p,h in hashes.items()),'Confirmation source changed during execution'
    result={'time':stamp(),'passed':len(rows)==15 and all(x['passed'] for x in rows),'master_seed':20261109,
            'method':'percentile','reported_coverage':.95,'noninferiority_coverage':.975,'noninferiority_quantile':.9875,
            'iterations':1000,'bootstrap_draws':2000,'source_hashes':hashes,'simulation':sorted(rows,key=lambda x:(x['scenario'],x['sc'],x['m'])),
            'scope':'Independent confirmation under author-fixed seed and unchanged gates; estimates with marginal binomial intervals, not proof of a universal error bound.'}
    save(output,result)
    if not result['passed']:raise SystemExit('Independent confirmation failed; collection continues, analysis remains unfrozen')

if __name__=='__main__':main()
