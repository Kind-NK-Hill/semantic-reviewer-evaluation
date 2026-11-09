"""Frozen estimands and decision functions. Codes: faithful=1, unfaithful=0, uncertain=2."""
from __future__ import annotations
import numpy as np
import os
from scipy.stats import binomtest, norm

def item_rate(votes,kind='accept'):
    a=np.asarray(votes,dtype=float)
    if a.ndim==1:a=a[:,None]
    valid=np.isfinite(a)
    hit=(a==1) if kind=='accept' else (a==0) if kind=='confirmed' else (a==2) if kind=='uncertain' else ((a==0)|(a==2))
    numerator=(hit&valid).sum(axis=1);denominator=valid.sum(axis=1)
    return np.divide(numerator,denominator,out=np.full(len(a),np.nan),where=denominator>0)

def bootstrap_distribution(values,groups,draws,generator):
    """Cluster percentile bootstrap; aggregate identical cluster sufficient statistics exactly."""
    values=np.asarray(values,dtype=float)
    if values.ndim==1:values=values[:,None]
    groups=np.asarray(groups)
    _,mapping=np.unique(groups,return_inverse=True)
    g=int(mapping.max()+1) if len(mapping) else 0
    if not g:return np.full((draws,values.shape[1]),np.nan)
    sums=np.zeros((g,values.shape[1]));counts=np.zeros_like(sums)
    np.add.at(sums,mapping,np.nan_to_num(values,nan=0))
    np.add.at(counts,mapping,np.isfinite(values).astype(float))
    patterns,freq=np.unique(np.column_stack([sums,counts]),axis=0,return_counts=True)
    weights=generator.multinomial(g,freq/freq.sum(),size=draws)
    k=values.shape[1];num=weights@patterns[:,:k];den=weights@patterns[:,k:]
    return np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)

def interval(values,groups,draws,generator):
    values=np.asarray(values,dtype=float)
    finite=np.isfinite(values)
    if not finite.any():return {'estimate':None,'low':None,'high':None,'n':0}
    vals=values[finite];grp=np.asarray(groups)[finite]
    method=os.environ.get('RC_BOOTSTRAP_METHOD','percentile')
    if method=='studentized':
        assert len(np.unique(grp))==len(grp),'Studentized candidate requires independently grouped item means'
        pair=bootstrap_distribution(np.column_stack([vals,vals**2]),grp,draws,generator)
        dist=pair[:,0];n=len(vals);point=float(np.mean(vals));se=float(np.std(vals,ddof=1)/np.sqrt(n)) if n>1 else 0.
        variance=np.maximum(0,pair[:,1]-pair[:,0]**2)/(n-1) if n>1 else np.zeros(draws)
        se_boot=np.sqrt(variance)
        pivot=np.divide(dist-point,se_boot,out=np.zeros(draws),where=se_boot>1e-15)
        pivot[(se_boot<=1e-15)&(dist>point+1e-12)]=np.inf
        pivot[(se_boot<=1e-15)&(dist<point-1e-12)]=-np.inf
        if se:
            qlo,qhi=np.quantile(pivot,[.025,.975],method='inverted_cdf')
            lo=max(-1.,point-qhi*se);hi=min(1.,point-qlo*se)
        else:lo=hi=point
    else:dist=bootstrap_distribution(vals,grp,draws,generator)[:,0]
    if method=='bca':
        # Diagnostic candidate only unless explicitly selected before freezing.
        point=float(np.mean(vals));equal=np.isclose(dist,point,rtol=0,atol=1e-12)
        fraction=(np.sum((dist<point)&~equal)+.5*np.sum(equal))/len(dist)
        z0=norm.ppf(np.clip(fraction,1/(2*len(dist)),1-1/(2*len(dist))))
        unique,inverse=np.unique(grp,return_inverse=True)
        totals=np.bincount(inverse,weights=vals);sizes=np.bincount(inverse)
        jack=(np.sum(vals)-totals)/(len(vals)-sizes) if len(unique)>1 else np.array([point])
        centered=np.mean(jack)-jack;den=6*np.sum(centered**2)**1.5
        acceleration=float(np.sum(centered**3)/den) if den else 0.
        z=norm.ppf([.025,.975]);adjusted=norm.cdf(z0+(z0+z)/(1-acceleration*(z0+z)))
        lo,hi=np.nanquantile(dist,np.clip(adjusted,0,1))
    elif method=='percentile':lo,hi=np.nanquantile(dist,[.025,.975])
    elif method!='studentized':raise ValueError('Unknown bootstrap method: '+method)
    result={'estimate':float(np.mean(vals)),'low':float(lo),'high':float(hi),'n':len(vals)}
    ni_coverage=float(os.environ.get('RC_NONINFERIORITY_COVERAGE','0.95'))
    if ni_coverage!=.95:
        assert method=='percentile' and ni_coverage==.975,'Only the author-approved percentile revision is supported'
        result['noninferiority_high']=float(np.nanquantile(dist,.9875))
        result['noninferiority_coverage']=.975
    return result

def compare(r1,x,labels,groups,draws,generator):
    r1=np.asarray(r1,float);x=np.asarray(x,float);labels=np.asarray(labels,dtype=bool);groups=np.asarray(groups)
    metrics={}
    for name,mask,kind,sign in [('leak_diff',~labels,'accept',1),('reject_diff',labels,'reject',1),('confirmed_diff',~labels,'confirmed',-1)]:
        a=item_rate(r1,kind);b=item_rate(x,kind)
        available=mask&np.isfinite(a)&np.isfinite(b)
        delta=sign*(b[available]-a[available])
        metrics[name]=interval(delta,groups[available],draws,generator)
        metrics[name]['excluded']=int(mask.sum()-available.sum())
    metrics['decision']=pair_decision(metrics)
    return metrics

def pair_decision(metrics):
    leak=metrics['leak_diff'];reject=metrics['reject_diff'];confirmed=metrics['confirmed_diff']
    if leak['low'] is not None and leak['low']>0:
        return 'r1_superior' if confirmed['low'] is not None and confirmed['low']>0 else 'more_rejection_or_abstention'
    lh=leak.get('noninferiority_high',leak['high']);rh=reject.get('noninferiority_high',reject['high'])
    if lh is not None and rh is not None and lh<.05 and rh<.05:return 'x_noninferior'
    return 'insufficient'

def final_decision(r0,r1g):
    if r0=='x_noninferior':return {'action':'replace_with_r0','rationale':'r0_noninferior','claims_superiority':False}
    if r0!='r1_superior':return {'action':'retain_r1','rationale':'insufficient_against_r0','claims_superiority':False}
    if r1g=='r1_superior':return {'action':'retain_r1','rationale':'r1_superior_to_both','claims_superiority':True}
    if r1g=='x_noninferior':return {'action':'replace_with_r1g','rationale':'r1_superior_to_r0_and_r1g_noninferior','claims_superiority':True}
    return {'action':'retain_r1','rationale':'r1_superior_to_r0_other_uncertain','claims_superiority':True}

def fill_missing(votes,labels,correct):
    out=np.array(votes,float,copy=True)
    truth=np.asarray(labels,bool)
    replacement=np.where(truth,1,0) if correct else np.where(truth,0,1)
    missing=~np.isfinite(out)
    out[missing]=np.broadcast_to(replacement[:,None],out.shape)[missing]
    return out

def kappa(votes,categories=(0,1)):
    a=np.asarray(votes)
    n,m=a.shape
    if not n or m<2:return None
    counts=np.column_stack([(a==c).sum(axis=1) for c in categories])
    observed=np.mean(((counts**2).sum(axis=1)-m)/(m*(m-1)))
    expected=np.sum((counts.sum(axis=0)/(n*m))**2)
    return None if np.isclose(expected,1) else float((observed-expected)/(1-expected))

def auxiliary(votes):
    a=np.asarray(votes,float);m=a.shape[1];a=a[np.isfinite(a).all(axis=1)]
    n=len(a);accepted=(a==1).astype(int)
    return {'n_complete':n,'m':m,'majority':((accepted.sum(axis=1)>=2).astype(int) if m==3 else None),
            'all_accept':(accepted.all(axis=1).astype(int) if m>=2 else None),
            'flip_rate':float(np.mean((accepted.min(axis=1)!=accepted.max(axis=1)))) if n and m>=2 else None,
            'kappa_binary':kappa(accepted) if m>=2 else None,'kappa_three':kappa(a,(0,1,2)) if m>=2 else None}

def mcnemar(a,b):
    a=np.asarray(a);b=np.asarray(b);ab=int(((a==1)&(b==0)).sum());ba=int(((a==0)&(b==1)).sum())
    return {'a_only':ab,'b_only':ba,'pvalue':float(binomtest(ab,ab+ba,.5).pvalue) if ab+ba else 1.0}

def power(m,q,rho,n=288):
    se=np.sqrt(q*(1+(m-1)*rho)/(m*n))
    return {'se':float(se),'minimum_detectable_difference':float(2.8*se),'noninferiority_probability_if_equal':float(norm.cdf(.05/se-1.96)) if se else 1.0}
