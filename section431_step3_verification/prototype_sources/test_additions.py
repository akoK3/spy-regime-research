import numpy as np
from section431_additions import construct_additions,DEFERRED
n=100
r=np.full(n,np.nan); r[1:]=0.001*np.sin(np.arange(1,n))
c=np.exp(np.cumsum(np.nan_to_num(r)))*100
v=np.full(n,1000.)
d=dict(r=r,close=c,volume=v,range=np.full(n,.002),first=np.array([0]),end=np.array([n]))
f=construct_additions(d)
assert len(f)==45, len(f)
assert all(np.isnan(f[k]).all() for k in DEFERRED)
assert np.isnan(f['bipower_15'][:15]).all()
assert np.isfinite(f['bipower_15'][15:]).all()
assert np.nanmin(f['jump_variation_15'])>=0
assert np.nanmax(f['drawdown_15'])<=0
assert np.nanmin(f['directional_efficiency_15'])>=0
assert np.nanmax(f['directional_efficiency_15'])<=1+1e-10
# Future edits do not change earlier calculations.
d2={k:(z.copy() if isinstance(z,np.ndarray) else z) for k,z in d.items()}
d2['r'][-1]=9.; d2['close'][-1]=10000.
f2=construct_additions(d2)
for k in f: assert np.allclose(f[k][:-1],f2[k][:-1],equal_nan=True)
# Missing return invalidates full-window candidates.
d3={k:(z.copy() if isinstance(z,np.ndarray) else z) for k,z in d.items()}
d3['r'][30]=np.nan
f3=construct_additions(d3)
assert np.isnan(f3['bipower_15'][30:45]).all()
print('PASS: synthetic feature shape, strict windows, bounds, missingness, future-edit invariance')
