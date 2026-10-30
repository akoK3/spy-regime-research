"""Section 4.3.1 additional SPY candidates, experimental amendment.

Inputs are session-indexed arrays in the format returned by section4_3_1_candidates.load_development.
No fitted model, selection, evaluation data, imputation, or cross-session rolling windows.
These are explicitly defined candidate operationalizations, not a retroactive frozen protocol.
"""
import numpy as np

WINDOWS=(15,30,60)

def construct_additions(d):
    r=np.asarray(d['r'],float); c=np.asarray(d['close'],float)
    v=np.asarray(d['volume'],float); rg=np.asarray(d['range'],float)
    n=len(r); f={}
    names=['close_location_proxy','overnight_return_open']
    for w in WINDOWS:
        names += [f'{k}{w}' for k in ('bipower_','jump_variation_','drawdown_','amihud_','skew_','kurtosis_excess_','variance_ratio2_','directional_efficiency_','vol_of_vol_','extreme_loss_','volume_variability_','volume_adjusted_range_','reversal_','return_autocorr1_')]
    names += ['lee_mykland_approx60']
    for name in names: f[name]=np.full(n,np.nan)
    # Close location requires bar High and Low, not available in existing d.
    # Overnight requires opening prices, not available in existing d.
    # Lee-Mykland requires a formally specified test statistic and calibration.
    for a,b in zip(d['first'],d['end']):
        for w in WINDOWS:
            for j in range(w,b-a):
                idx=a+j; x=r[idx-w+1:idx+1]
                if not np.isfinite(x).all(): continue
                sq=np.sum(x*x); bp=(np.pi/2)*np.sum(np.abs(x[1:]*x[:-1]))
                f[f'bipower_{w}'][idx]=bp
                f[f'jump_variation_{w}'][idx]=max(0.,sq-bp)
                # Rolling drawdown is computed from w+1 exact observed closes.
                prices=c[idx-w:idx+1]
                if np.isfinite(prices).all() and np.max(prices)>0:
                    f[f'drawdown_{w}'][idx]=prices[-1]/np.max(prices)-1
                    f[f'directional_efficiency_{w}'][idx]=abs(np.log(prices[-1]/prices[0]))/np.sum(np.abs(x)) if np.sum(np.abs(x))>0 else np.nan
                if np.isfinite(v[idx-w+1:idx+1]).all():
                    vv=v[idx-w+1:idx+1]
                    dollar=vv*c[idx-w+1:idx+1]
                    if np.isfinite(dollar).all() and (dollar>0).all():
                        f[f'amihud_{w}'][idx]=np.mean(np.abs(x)/dollar)
                    if vv.mean()>0: f[f'volume_variability_{w}'][idx]=vv.std(ddof=1)/vv.mean()
                    ranges=rg[idx-w+1:idx+1]
                    if np.isfinite(ranges).all() and (vv>0).all():
                        f[f'volume_adjusted_range_{w}'][idx]=np.mean(ranges/vv)
                if w>=15:
                    s=x.std(ddof=0)
                    if s>0:
                        z=(x-x.mean())/s
                        f[f'skew_{w}'][idx]=np.mean(z**3)
                        f[f'kurtosis_excess_{w}'][idx]=np.mean(z**4)-3
                if w>=15 and x.var()>0:
                    paired=x[:-1]+x[1:]
                    f[f'variance_ratio2_{w}'][idx]=np.mean(paired**2)/(2*np.mean(x*x)) if np.mean(x*x)>0 else np.nan
                    f[f'return_autocorr1_{w}'][idx]=np.corrcoef(x[:-1],x[1:])[0,1] if x[:-1].std()>0 and x[1:].std()>0 else np.nan
                f[f'extreme_loss_{w}'][idx]=np.min(x)
                f[f'reversal_{w}'][idx]=float(np.sign(np.sum(x[:w//2])) != np.sign(np.sum(x[w//2:]))) if np.sum(x[:w//2])!=0 and np.sum(x[w//2:])!=0 else np.nan
                # Vol-of-vol: sample SD of non-overlapping 5-return realized volatility blocks.
                if w%5==0 and w>=15:
                    rv=np.sqrt(np.sum(x.reshape(-1,5)**2,axis=1))
                    f[f'vol_of_vol_{w}'][idx]=rv.std(ddof=1)
    return f

DEFERRED={
 'overnight_return_open':'Requires separately audited session-open/previous-close prices, dividend conventions and timestamp availability; source d lacks Open.',
 'close_location_proxy':'Requires High and Low levels and Close; current d retains only log(High/Low).',
 'lee_mykland_approx60':'Formal Lee-Mykland statistic requires local spot-volatility estimator, boundary rules and null calibration; uncalibrated surrogate would be misleading.',
}
