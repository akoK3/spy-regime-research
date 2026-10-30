#!/usr/bin/env python3
"""Step 3 one-pass audit. Run in Downloads beside section431_step3_verification.
Requires the original Section 3 ETF files. No evaluation data are loaded.
Reports FAIL for unimplemented/deferred families rather than silently approving them.
"""
import sys, json, hashlib, traceback, datetime, time, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"section431_step3_verification"/"prototype_sources"
sys.path.insert(0,str(SRC))
from section4_3_1_candidates import load_development, construct, selected_csv, ns
from section431_additions import construct_additions, DEFERRED

OUT=ROOT/"section431_step3_all_in_one_results"
OUT.mkdir(exist_ok=True)
CONFIG={
"RAW":("2022-03-07","2024-12-23","section3_10_alignment_results/canonical_panel_RAW_1m.csv.gz","section3_4_etf_results/etf_observed_SPY_RAW.csv.gz"),
"LEGACY":("2003-01-02","2018-12-21","section3_10_alignment_results/canonical_panel_LEGACY_1m.csv.gz","section3_4_etf_results/etf_observed_SPY_LEGACY.csv.gz")
}
EXPECTED_ORIGINAL=35
EXPECTED_ADDITIONAL=46  # 45 from construct_additions (3 were NaN placeholders) + lee_mykland_jump60
OHLC_KEYS=("open","high","low")
SEED=43103
ATOL=1e-10
RTOL=1e-9
START=time.time()
SLICE_ERAS={"LEGACY","RAW"}
SLICE_SESSIONS=40
SLICE_COMPARE=15  # only the last 15 sessions of each slice are compared with the full run
SLICE_WARMUP=SLICE_SESSIONS-SLICE_COMPARE  # 25 sessions of history; relative volume needs 20
SLICE_KEYS=("t","available","day","slot","r","valid","close","range","volume")+OHLC_KEYS

def log(message):
    print(f"[{(time.time()-START)/60:7.1f} min] {message}",flush=True)

class SessionProgress:
    """Yields session starts unchanged and logs progress; values are not altered."""
    def __init__(self,values,label):
        self.values,self.label=values,label
    def __len__(self):
        return len(self.values)
    def __iter__(self):
        n=len(self.values); step=max(1,n//20); began=time.time()
        for i,value in enumerate(self.values):
            if i and i%step==0:
                spent=time.time()-began
                log(f"  {self.label}: session {i}/{n}, about {spent/i*(n-i)/60:.1f} min left in this pass")
            yield value

def file_path(rel):
    p=ROOT/rel
    if p.exists(): return p
    alt=ROOT/Path(rel).name
    if alt.exists(): return alt
    raise FileNotFoundError(f"Required source file not found: {p}")

def copied(d):
    return {k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in d.items()}

LM_NTESTS=390
LM_ALPHA=.01

def lm_threshold():
    k=np.sqrt(2/np.pi); a=np.sqrt(2*np.log(LM_NTESTS))
    c0=a/k-(np.log(np.pi)+np.log(np.log(LM_NTESTS)))/(2*k*a)
    s0=1/(k*a)
    return c0-s0*np.log(-np.log(1-LM_ALPHA))

def load_ohlc(spec,d):
    """Open/High/Low levels on the panel grid; the audited loader keeps only log(High/Low)."""
    e=selected_csv(spec["etf_file"],["utc_minute_start","session_date_ny","Open","High","Low","Close"],spec["first_session"],spec["last_session"])
    j=pd.Index(d["t"]).get_indexer(ns(e.utc_minute_start))
    if (j<0).any(): raise AssertionError("OHLC row outside calendar grid")
    if not np.allclose(d["close"][j],e["Close"].to_numpy(float),rtol=1e-12,atol=0): raise AssertionError("Close differs between loads")
    out={}
    for key,col in zip(OHLC_KEYS,("Open","High","Low")):
        z=np.full(len(d["t"]),np.nan); z[j]=e[col].to_numpy(float); out[key]=z
    return out

def construct_deferred(d):
    """close_location_proxy, overnight_return_open, lee_mykland_approx60/jump60, ported from section-4.3.1.py."""
    r,c,h,l,o,v=(d[k] for k in ("r","close","high","low","open","volume"))
    n=len(r)
    loc,on,stat,jump=(np.full(n,np.nan) for _ in range(4))
    with np.errstate(invalid="ignore"):
        ok=(c>0)&(h>=c)&(c>=l)&(l>0)&(v>=0)&np.isfinite(c+h+l+v)&(h>l)
    loc[ok]=(c[ok]-l[ok])/(h[ok]-l[ok])
    threshold=lm_threshold()
    firsts,ends=list(d["first"]),list(d["end"])
    for k,(a,b) in enumerate(zip(firsts,ends)):
        if k>0:
            op,pc=o[a],c[ends[k-1]-1]
            if np.isfinite(op) and op>0 and np.isfinite(pc) and pc>0: on[a:b]=np.log(op/pc)
        m=b-a
        if m<=60: continue
        x=r[a:b]
        with np.errstate(invalid="ignore"):
            prior=np.lib.stride_tricks.sliding_window_view(x,60)[:m-60]  # row i = x[i..i+59], used for position i+60
            pa=np.abs(prior)
            local_var=(np.pi/2)*(pa[:,1:]*pa[:,:-1]).sum(axis=1)/59
            t=np.arange(60,m); cur=x[t]
            use=np.isfinite(prior).all(axis=1)&(local_var>0)&np.isfinite(cur)
        s=np.full(len(t),np.nan); s[use]=cur[use]/np.sqrt(local_var[use])
        stat[a+t]=s
        jump[a+t[use]]=(np.abs(s[use])>threshold).astype(float)
    return {"close_location_proxy":loc,"overnight_return_open":on,"lee_mykland_approx60":stat,"lee_mykland_jump60":jump}

def calculate(d,label="features"):
    log(f"  {label}: original features")
    a,_=construct(d)
    log(f"  {label}: additional features")
    view=dict(d)
    view["first"]=SessionProgress(d["first"],label)
    b=construct_additions(view)
    b.update(construct_deferred(d))
    log(f"  {label}: done")
    return {"original":a,"additional":b}

def compare_prefix(before,after,cut):
    errors=[]
    for family in before:
        for key,values in before[family].items():
            x=np.asarray(values[:cut],float)
            y=np.asarray(after[family][key][:cut],float)
            if not np.allclose(x,y,rtol=RTOL,atol=ATOL,equal_nan=True):
                errors.append(f"{family}.{key}")
    return errors

def slice_sessions(d,lo,hi):
    """Sessions lo..hi-1 as a standalone copy with positions rebased to zero."""
    start,stop=int(d["first"][lo]),int(d["end"][hi-1])
    z={k:d[k][start:stop].copy() for k in SLICE_KEYS}
    z["era"]=d["era"]
    z["first"]=d["first"][lo:hi]-start
    z["end"]=d["end"][lo:hi]-start
    return z,start

def compare_slice(full,part,offset,lo,hi):
    """Compare full-run positions lo..hi-1 with the same rows of a sliced run."""
    errors=[]
    for family in full:
        for key,values in full[family].items():
            x=np.asarray(values[lo:hi],float)
            y=np.asarray(part[family][key][lo-offset:hi-offset],float)
            if not np.allclose(x,y,rtol=RTOL,atol=ATOL,equal_nan=True):
                errors.append(f"{family}.{key}")
    return errors

def truncate(d,cut):
    z=copied(d)
    for k in ("t","available","day","slot","r","valid","close","range","volume")+OHLC_KEYS:
        z[k]=z[k][:cut]
    first=z["first"][z["first"]<cut]
    z["first"]=first
    z["end"]=np.r_[first[1:],cut]
    return z

def independent_checks(d,features):
    """Independent scalar oracles on actual source arrays; not merely reruns."""
    errors=[]
    o=features["original"]; a=features["additional"]
    rng=np.random.default_rng(SEED)
    sessions=rng.choice(len(d["first"]),size=min(10,len(d["first"])),replace=False)
    for s in sessions:
        lo,hi=int(d["first"][s]),int(d["end"][s])
        for w in (15,30,60):
            if hi-lo<=w: continue
            for j in rng.choice(np.arange(lo+w,hi),size=min(4,hi-lo-w),replace=False):
                j=int(j); x=d["r"][j-w+1:j+1]
                if not np.isfinite(x).all(): continue
                cases={
                  f"rv{w}_strict":np.sqrt(np.sum(x*x)),
                  f"downside{w}_strict":np.sqrt(np.sum(np.minimum(x,0)**2)),
                  f"momentum{w}_strict":np.sum(x),
                  f"bipower_{w}":np.pi/2*np.sum(np.abs(x[1:]*x[:-1])),
                  f"jump_variation_{w}":max(0.,np.sum(x*x)-np.pi/2*np.sum(np.abs(x[1:]*x[:-1]))),
                  f"extreme_loss_{w}":np.min(x)
                }
                prices=d["close"][j-w:j+1]
                if np.isfinite(prices).all() and np.all(prices>0):
                    cases[f"drawdown_{w}"]=prices[-1]/max(prices)-1
                    cases[f"directional_efficiency_{w}"]=abs(np.log(prices[-1]/prices[0]))/np.sum(abs(x)) if np.sum(abs(x)) else np.nan
                for key,expected in cases.items():
                    group=o if key in o else a
                    actual=group[key][j]
                    if not np.isclose(actual,expected,rtol=RTOL,atol=ATOL,equal_nan=True):
                        errors.append(f"{key}@{j}: {actual} != {expected}")
    return errors

def sanity(features):
    errors=[]; summary={}
    for group,fs in features.items():
        for name,x in fs.items():
            x=np.asarray(x,dtype=float)
            if np.isinf(x).any(): errors.append(f"{group}.{name}: infinity")
            finite=x[np.isfinite(x)]
            summary[f"{group}.{name}"]={"finite":int(len(finite)),"total":int(len(x))}
            if ("drawdown_" in name and np.any(finite>ATOL) or
                "directional_efficiency_" in name and np.any((finite < -ATOL)|(finite > 1+ATOL)) or
                "jump_variation_" in name and np.any(finite < -ATOL) or
                "bipower_" in name and np.any(finite < -ATOL) or
                "close_location" in name and np.any((finite < -ATOL)|(finite > 1+ATOL)) or
                "lee_mykland_jump" in name and np.any((finite != 0)&(finite != 1))):
                errors.append(f"{group}.{name}: theoretical bound violation")
    return errors,summary

BOUNDARY_LAST_LEGACY="2022-03-04"
BOUNDARY_FIRST_RAW="2022-03-07"
FORMULA_RTOL=1e-8
FORMULA_ATOL=1e-16

def window_length(group,name):
    """Bars of within-session history an output needs, or None if it has no such window."""
    if group=="original":
        if name.startswith("shock_prior"): return int(re.search(r"\d+",name).group())+1
        if name.startswith(("rv","downside","momentum")): return int(re.match(r"[a-z]+(\d+)",name).group(1))
        return None
    m=re.search(r"_(\d+)$",name) or re.search(r"(?:approx|jump)(\d+)$",name)
    return int(m.group(1)) if m else None

def provider_isolation(era,d,f):
    """Real-data structural checks: nothing can reach across a session or era edge."""
    errors=[]
    days=sorted(set(d["day"].tolist()))
    if era=="LEGACY" and days[-1]>BOUNDARY_LAST_LEGACY: errors.append(f"LEGACY contains session {days[-1]} after {BOUNDARY_LAST_LEGACY}")
    if era=="RAW" and days[0]<BOUNDARY_FIRST_RAW: errors.append(f"RAW contains session {days[0]} before {BOUNDARY_FIRST_RAW}")
    if era not in ("LEGACY","RAW"): errors.append(f"unknown era {era}")
    if np.isfinite(d["r"][d["first"]]).any(): errors.append("return present at a session open")
    for group,fs in f.items():
        for name,x in fs.items():
            w=window_length(group,name)
            if w is not None and np.isfinite(np.asarray(x,float)[d["slot"]<w]).any():
                errors.append(f"{group}.{name}: value inside the first {w} bars of a session")
    # Relative volume needs 10 prior sessions of this era, so the era's first 10 sessions must be NaN.
    warm_end=int(d["end"][min(9,len(d["first"])-1)])
    for name in ("relative_volume20","log_relative_volume20"):
        if np.isfinite(f["original"][name][:warm_end]).any(): errors.append(f"{name}: value before 10 prior sessions of this era")
    if np.isfinite(f["additional"]["overnight_return_open"][:int(d["end"][0])]).any(): errors.append("overnight value in the era's first session")
    return errors

def synthetic_panel(sessions=24,length=100):
    rng=np.random.default_rng(SEED+7)
    n=sessions*length
    slot=np.tile(np.arange(length),sessions)
    day=np.repeat([f"2022-04-{s+1:02d}" for s in range(sessions)],length)
    first=np.arange(0,n,length); end=first+length
    steps=rng.standard_t(4,size=n)*7e-4
    steps[[380,1775]]*=15  # two large moves so the Lee-Mykland flag takes both values
    logp=np.empty(n)
    for s in range(sessions):
        a=s*length
        logp[a:a+length]=np.log(100)+rng.normal(0,.01)+np.cumsum(steps[a:a+length])
    close=np.exp(logp)
    missing=rng.random(n)<.004
    missing[first[5]]=True; missing[end[8]-1]=True  # session 5 open and session 8 close missing: overnight NaN for sessions 5 and 9
    volume=rng.lognormal(7,.5,size=n)
    volume[rng.random(n)<.005]=0.
    up,down=np.abs(rng.normal(0,4e-4,size=n)),np.abs(rng.normal(0,4e-4,size=n))
    flat=rng.random(n)<.01
    up[flat]=0.; down[flat]=0.  # zero-range bars: close location must be NaN
    high,low=close*np.exp(up),close*np.exp(-down)
    open_=close*np.exp(rng.normal(0,3e-4,size=n))
    rng_log=np.log(high/low)
    for z in (close,volume,rng_log,high,low,open_): z[missing]=np.nan
    prev=np.r_[np.nan,close[:-1]]
    valid=(slot>0)&np.isfinite(close)&np.isfinite(prev)
    r=np.full(n,np.nan); r[valid]=np.log(close[valid]/prev[valid])
    t=np.arange(n,dtype=np.int64)*60_000_000_000
    return dict(era="SYNTHETIC",t=t,available=t+60_000_000_000,day=day,slot=slot,r=r,valid=valid,
                close=close,range=rng_log,volume=volume,first=first,end=end,open=open_,high=high,low=low)

def oracle_features(d):
    """Plain per-row numpy calculations written from the definitions, not from the code under test."""
    r,c,v,rg,slot=d["r"],d["close"],d["volume"],d["range"],d["slot"]
    n=len(r); out={}
    def new(name):
        out[name]=np.full(n,np.nan); return out[name]
    out["return_1m"]=r.copy(); out["abs_return_1m"]=np.abs(r)
    out["intrabar_range_log"]=rg.copy(); out["raw_volume"]=v.copy()
    out["log_raw_volume"]=np.array([np.log(x) if x>0 else np.nan for x in v])
    rel=new("relative_volume20"); logrel=new("log_relative_volume20")
    spans=list(zip(d["first"],d["end"]))
    for k,(a,b) in enumerate(spans):
        for i in range(a,b):
            past=[]
            for p in range(max(0,k-20),k):
                hit=np.flatnonzero(slot[spans[p][0]:spans[p][1]]==slot[i])
                if len(hit) and v[spans[p][0]+hit[0]]>0: past.append(v[spans[p][0]+hit[0]])
            if len(past)>=10:
                base=float(np.median(past))
                if np.isfinite(v[i]) and v[i]>=0 and base>0:
                    rel[i]=v[i]/base
                    if rel[i]>0: logrel[i]=np.log(rel[i])
    for w in (5,10,15,30,60):
        rv,ds,mom=new(f"rv{w}_strict"),new(f"downside{w}_strict"),new(f"momentum{w}_strict")
        part,ep=new(f"rv{w}_partial90"),new(f"momentum{w}_endpoint")
        d15=new("downside15_partial90") if w==15 else None
        for a,b in spans:
            for j in range(w,b-a):
                i=a+j; x=r[i-w+1:i+1]; xs=x[np.isfinite(x)]; m=len(xs)
                if m==w:
                    rv[i]=np.sqrt(np.sum(xs**2)); ds[i]=np.sqrt(np.sum(np.minimum(xs,0)**2)); mom[i]=np.sum(xs)
                if m>=int(np.ceil(.9*w)):
                    part[i]=np.sqrt(np.sum(xs**2)*w/m)
                    if d15 is not None: d15[i]=np.sqrt(np.sum(np.minimum(xs,0)**2)*w/m)
                if np.isfinite(c[i]) and np.isfinite(c[i-w]): ep[i]=np.log(c[i]/c[i-w])
    s5,shock=new("rv60_sampled5_exact"),new("shock_prior60_mad")
    for a,b in spans:
        for j in range(60,b-a):
            pts=c[a+j-np.arange(0,61,5)]
            if np.isfinite(pts).all(): s5[a+j]=np.sqrt(np.sum(np.diff(np.log(pts))**2))
        for j in range(61,b-a):
            win=r[a+j-60:a+j+1]
            if np.isfinite(win).all():
                past=win[:60]; med=np.median(past); scale=1.4826*np.median(np.abs(past-med))
                if scale>0: shock[a+j]=(win[60]-med)/scale
    loc,on,lm,lj=(new(k) for k in ("close_location_proxy","overnight_return_open","lee_mykland_approx60","lee_mykland_jump60"))
    o,h,l=d["open"],d["high"],d["low"]
    ln=np.log(LM_NTESTS); kk=2/np.pi
    thr=np.sqrt(2*ln)/np.sqrt(kk)-(np.log(np.pi)+np.log(ln))/(2*np.sqrt(kk)*np.sqrt(2*ln))+(1/(np.sqrt(kk)*np.sqrt(2*ln)))*(-np.log(-np.log(1-LM_ALPHA)))
    for k,(a,b) in enumerate(spans):
        for i in range(a,b):
            if c[i]>0 and h[i]>=c[i]>=l[i] and l[i]>0 and v[i]>=0 and np.isfinite(c[i]+h[i]+l[i]+v[i]) and h[i]>l[i]:
                loc[i]=(c[i]-l[i])/(h[i]-l[i])
        if k>0:
            op,pc=o[a],c[spans[k-1][1]-1]
            if np.isfinite(op) and op>0 and np.isfinite(pc) and pc>0: on[a:b]=np.log(op/pc)
        for t in range(60,b-a):
            past=r[a+t-60:a+t]
            if np.isfinite(past).all() and np.isfinite(r[a+t]):
                lv=np.pi/2*np.mean(np.abs(past[1:])*np.abs(past[:-1]))
                if lv>0:
                    lm[a+t]=r[a+t]/np.sqrt(lv); lj[a+t]=float(abs(lm[a+t])>thr)
    for w in (15,30,60):
        A={k:new(f"{k}{w}") for k in ("bipower_","jump_variation_","drawdown_","amihud_","skew_","kurtosis_excess_","variance_ratio2_","directional_efficiency_","vol_of_vol_","extreme_loss_","volume_variability_","volume_adjusted_range_","reversal_","return_autocorr1_")}
        for a,b in spans:
            for j in range(w,b-a):
                i=a+j; x=r[i-w+1:i+1]
                if not np.isfinite(x).all(): continue
                bp=np.pi/2*np.sum(np.abs(x[1:])*np.abs(x[:-1]))
                A["bipower_"][i]=bp; A["jump_variation_"][i]=max(0.,np.sum(x**2)-bp)
                p=c[i-w:i+1]
                if np.isfinite(p).all() and p.max()>0:
                    A["drawdown_"][i]=p[-1]/p.max()-1
                    path=np.sum(np.abs(x))
                    if path>0: A["directional_efficiency_"][i]=abs(np.log(p[-1]/p[0]))/path
                vv=v[i-w+1:i+1]
                if np.isfinite(vv).all():
                    dollar=vv*c[i-w+1:i+1]
                    if np.isfinite(dollar).all() and (dollar>0).all(): A["amihud_"][i]=np.mean(np.abs(x)/dollar)
                    if vv.mean()>0: A["volume_variability_"][i]=np.std(vv,ddof=1)/vv.mean()
                    ranges=rg[i-w+1:i+1]
                    if np.isfinite(ranges).all() and (vv>0).all(): A["volume_adjusted_range_"][i]=np.mean(ranges/vv)
                mean=x.mean(); var=np.mean((x-mean)**2)
                if var>0:
                    z=(x-mean)/np.sqrt(var)
                    A["skew_"][i]=np.mean(z**3); A["kurtosis_excess_"][i]=np.mean(z**4)-3
                    m2=np.mean(x*x)
                    if m2>0: A["variance_ratio2_"][i]=np.mean((x[:-1]+x[1:])**2)/(2*m2)
                    u,l=x[:-1],x[1:]
                    if u.std()>0 and l.std()>0:
                        A["return_autocorr1_"][i]=np.sum((u-u.mean())*(l-l.mean()))/np.sqrt(np.sum((u-u.mean())**2)*np.sum((l-l.mean())**2))
                A["extreme_loss_"][i]=x.min()
                s1,s2=x[:w//2].sum(),x[w//2:].sum()
                if s1!=0 and s2!=0: A["reversal_"][i]=float(np.sign(s1)!=np.sign(s2))
                A["vol_of_vol_"][i]=np.sqrt((x.reshape(-1,5)**2).sum(axis=1)).std(ddof=1)
    return out

def formula_all_outputs():
    """Every output of both generators against the oracle on one small synthetic panel."""
    d=synthetic_panel()
    code={**construct(d)[0],**construct_additions(d),**construct_deferred(d)}
    oracle=oracle_features(d)
    per_output={}; errors=[]
    if set(code)!=set(oracle) or len(code)!=EXPECTED_ORIGINAL+EXPECTED_ADDITIONAL:
        errors.append(f"output sets differ: code={len(code)} oracle={len(oracle)} missing_in_oracle={sorted(set(code)-set(oracle))[:5]} missing_in_code={sorted(set(oracle)-set(code))[:5]}")
    for name in sorted(set(code)&set(oracle)):
        x=np.asarray(code[name],float); y=np.asarray(oracle[name],float)
        finite=int(np.isfinite(x).sum())
        same=np.array_equal(np.isfinite(x),np.isfinite(y)) and np.allclose(x,y,rtol=FORMULA_RTOL,atol=FORMULA_ATOL,equal_nan=True)
        both=np.isfinite(x)&np.isfinite(y)
        err=float(np.max(np.abs(x[both]-y[both])/np.maximum(np.abs(y[both]),1e-300))) if both.any() else None
        ok=same and finite>0
        per_output[name]={"status":"PASS" if ok else "FAIL","finite":finite,"oracle_finite":int(np.isfinite(y).sum()),"max_rel_err":err}
        if not ok: errors.append(f"{name}: {per_output[name]}")
    flags=np.asarray(code["lee_mykland_jump60"],float)
    if not (np.nansum(flags==1)>0 and np.nansum(flags==0)>0): errors.append("lee_mykland_jump60: synthetic panel did not exercise both flag values")
    verified=sum(v["status"]=="PASS" for v in per_output.values())
    return {"status":"PASS" if not errors else "FAIL","outputs_compared":len(per_output),"formulas_verified":verified,
            "lm_threshold":lm_threshold(),"errors":errors[:30],"per_output":per_output,
            "scope":"synthetic 24x100 panel with missing bars, zero volume, zero-range bars, missing open/close endpoints and two large moves"}

def run(era,config):
    checks={}; notes=[]; report={"era":era,"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"checks":checks}
    try:
        first,last,panel,etf=config
        spec={"first_session":first,"last_session":last,"panel_file":str(file_path(panel)),"etf_file":str(file_path(etf))}
        log(f"{era}: loading panel and ETF files")
        d=load_development(era,spec)
        d.update(load_ohlc(spec,d))
        log(f"{era}: loaded {len(d['r'])} rows, {len(d['first'])} sessions")
        f=calculate(d,f"{era} full run")
        log(f"{era}: hashing source files")
        report["source_hashes"]={key:hashlib.sha256(Path(value).read_bytes()).hexdigest() for key,value in (("panel",spec["panel_file"]),("etf",spec["etf_file"]))}
        checks["inventory"]={"status":"PASS" if len(f["original"])==EXPECTED_ORIGINAL and len(f["additional"])==EXPECTED_ADDITIONAL else "FAIL",
           "original_count":len(f["original"]),"additional_output_count":len(f["additional"])}
        log(f"{era}: formula checks, all 81 outputs, synthetic panel")
        checks["formula_all_outputs"]=formula_all_outputs()
        log(f"{era}: formula spot checks")
        errors=independent_checks(d,f)
        checks["formula_spot_checks"]={"status":"PASS" if not errors else "FAIL","errors":errors[:30],
          "scope":"independent scalar checks for selected implemented formulas, NOT all formulas"}
        rng=np.random.default_rng(SEED)
        cuts=[]
        cut_sessions=[int(i) for i in rng.choice(np.arange(30,len(d["first"])-1),size=min(5,max(0,len(d["first"])-31)),replace=False)]
        for i in cut_sessions:
            cuts.append(int(d["end"][i]))
        prefix_errors=[]
        for number,(i,cut) in enumerate(zip(cut_sessions,cuts),1):
            label=f"{era} prefix {number}/{len(cuts)}"
            if era in SLICE_ERAS:
                lo=max(0,i-SLICE_SESSIONS+1)
                part,offset=slice_sessions(d,lo,i+1)
                small=calculate(part,label)
                compare_from=int(d["first"][lo+SLICE_WARMUP]) if lo else 0
                prefix_errors.extend(compare_slice(f,small,offset,compare_from,cut))
            else:
                small=calculate(truncate(d,cut),label)
                prefix_errors.extend(compare_prefix(f,small,cut))
            del small
        checks["real_train_prefix_invariance"]={"status":"PASS" if not prefix_errors else "FAIL","cuts":cuts,"errors":prefix_errors[:30],
          "method":f"{SLICE_SESSIONS}-session slice ending at the cut, rebuilt alone; last {SLICE_COMPARE} sessions of the slice compared with the full run" if era in SLICE_ERAS else "full prefix recomputed"}
        isolation_errors=[]
        chosen=rng.choice(np.arange(30,len(d["first"])-1),size=min(4,max(0,len(d["first"])-31)),replace=False)
        for number,i in enumerate(chosen,1):
            label=f"{era} isolation {number}/{len(chosen)}"
            if era in SLICE_ERAS:
                first_session=max(0,int(i)-SLICE_SESSIONS+1)
                altered,offset=slice_sessions(d,first_session,int(i)+1)
                # The blanked session is the slice's last one; compare the 15 sessions before it.
                compare_from=int(d["first"][first_session+SLICE_WARMUP-1]) if first_session else 0
            else:
                altered,offset,compare_from=copied(d),0,0
            lo,hi=int(d["first"][i])-offset,int(d["end"][i])-offset
            altered["r"][lo:hi]=np.nan
            altered["valid"][lo:hi]=False
            altered["close"][lo:hi]=np.nan
            altered["volume"][lo:hi]=np.nan
            altered["range"][lo:hi]=np.nan
            for key in OHLC_KEYS: altered[key][lo:hi]=np.nan
            changed=calculate(altered,label)
            # Prior session must not change; later sessions may legitimately
            # change because relative volume uses prior 20 sessions.
            if era in SLICE_ERAS:
                isolation_errors.extend(compare_slice(f,changed,offset,compare_from,lo+offset))
            else:
                isolation_errors.extend(compare_prefix(f,changed,lo))
            del altered,changed
        checks["prior_session_isolation"]={"status":"PASS" if not isolation_errors else "FAIL","errors":isolation_errors[:30],
          "method":f"{SLICE_SESSIONS}-session slice ending at the blanked session, rebuilt alone; the {SLICE_COMPARE} sessions before the blanked one compared with the full run" if era in SLICE_ERAS else "full era recomputed"}
        log(f"{era}: numerical sanity checks")
        errors,stats=sanity(f)
        checks["numerical_sanity"]={"status":"PASS" if not errors else "FAIL","errors":errors[:30]}
        report["coverage_summary"]=stats
        deferred=[k for k in DEFERRED if k in f["additional"] and not np.isfinite(f["additional"][k]).any()]
        checks["deferred_implementations"]={"status":"FAIL" if deferred else "PASS","unimplemented":deferred}
        # Provider isolation: independently load one era at a time, never concatenate.
        provider_errors=provider_isolation(era,d,f)
        checks["provider_isolation"]={"status":"PASS" if not provider_errors else "FAIL","errors":provider_errors[:30],
          "method":f"era-scoped loader; session dates on the correct side of {BOUNDARY_LAST_LEGACY}/{BOUNDARY_FIRST_RAW}; no value inside a window's first bars of a session; first 10 sessions have no relative volume; first-session overnight NaN"}
        report["status"]="PASS" if all(v["status"]=="PASS" for v in checks.values()) else "FAIL"
    except Exception:
        checks["execution"]={"status":"FAIL","traceback":traceback.format_exc()}
        report["status"]="FAIL"
    report["notes"]=notes
    target=OUT/f"step3_{era}_report.json"
    target.write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    print(f"{era}: {report['status']} — {target}")
    for k,v in checks.items(): print(f"  {k}: {v['status']}")
    return report

if __name__=="__main__":
    results=[run(era,CONFIG[era]) for era in (sys.argv[1:] or CONFIG)]
    saved={era:json.loads((OUT/f"step3_{era}_report.json").read_text(encoding="utf-8"))["status"] for era in CONFIG if (OUT/f"step3_{era}_report.json").exists()}
    (OUT/"step3_summary.json").write_text(json.dumps({"reports":saved,"rule":"an era is PASS only if every check in its report is PASS"},indent=2),encoding="utf-8")
    sys.exit(0 if all(x["status"]=="PASS" for x in results) else 1)
