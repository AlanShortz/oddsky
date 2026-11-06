import numpy as np, pandas as pd, sys
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
from nss_rv_test import load
d=pd.concat([load(False),load(True)]);d=d[d.nss_solution_type=='Orbital'].copy()
print('hist log10 e at low end:',np.histogram(np.log10(d.eccentricity.clip(lower=1e-6)),bins=[-6.01,-5,-4,-3.5,-3,-2.5,-2,-1.5,-1,-.5,0])[0])
print('flags (col) value counts for e<1e-3:',d[d.eccentricity<1e-3]['flags'].value_counts().head(5).to_dict(),' all:',d['flags'].value_counts().head(5).to_dict())
print('e quantiles among e<0.01',d[d.eccentricity<.01].eccentricity.describe().round(5).to_dict())
def ratio(x):
    rr=[]
    for g in range(12,16):
        pg,mg=x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense>0)],x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense<0)]
        if min(len(pg),len(mg))>=8: rr.append((pg.parallax_error.median()/mg.parallax_error.median(),len(pg)+len(mg)))
    return np.average([q[0] for q in rr],weights=[q[1] for q in rr]) if rr else np.nan
def A(x): return (x.sense.mean(),np.sqrt((1-x.sense.mean()**2)/max(len(x),1)),len(x))
groups=[('e<1e-3',0,1e-3),('1e-3<=e<0.05',1e-3,.05),('.05-.1',.05,.1),('.1-.2',.1,.2),('.2-.4',.2,.4),('.4-1',.4,1.01)]
for lo,hi in [(200,300),(300,340),(340,390),(390,450),(450,600),(600,700),(700,800),(800,900),(900,1100),(1100,3000)]:
    s=d[(d.period>=lo)&(d.period<hi)];o=[]
    for nm,e0,e1 in groups:
        x=s[(s.eccentricity>=e0)&(s.eccentricity<e1)]
        o.append('%s r=%.2f A=%+.3f±%.3f(%d)'%(nm,ratio(x),*A(x)))
    print(lo,hi,' | '.join(o))
# bootstrap the key comparison 650-850
rng=np.random.default_rng(1)
for lo,hi in [(650,850),(700,800),(300,450)]:
  for nm,e0,e1 in groups[:3]:
    x=d[(d.period>=lo)&(d.period<hi)&(d.eccentricity>=e0)&(d.eccentricity<e1)&(d.phot_g_mean_mag>=12)&(d.phot_g_mean_mag<16)]
    b=[ratio(x.iloc[rng.integers(0,len(x),len(x))]) for _ in range(200)]
    print(lo,hi,nm,'ratio %.3f ± %.3f, N=%d'%(ratio(x),np.nanstd(b),len(x)))
