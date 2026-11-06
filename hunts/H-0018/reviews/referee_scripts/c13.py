import numpy as np, pandas as pd, sys
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
from nss_rv_test import load
import handedness as hd
d=pd.concat([load(False),load(True)]);d=d[d.nss_solution_type=='Orbital'].copy()
d=d[(d.phot_g_mean_mag>=12)&(d.phot_g_mean_mag<16)]
G=[('e<5e-4',0,5e-4),('5e-4..6e-3',5e-4,6e-3),('6e-3..0.05',6e-3,.05),('.05-.1',.05,.1)]
rng=np.random.default_rng(1)
def rat(x):
    rr=[]
    for g in range(12,16):
        p,m=x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense>0)],x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense<0)]
        if min(len(p),len(m))>=5: rr.append((p.parallax_error.median()/m.parallax_error.median(),len(p)+len(m)))
    return np.average([q[0] for q in rr],weights=[q[1] for q in rr]) if rr else np.nan
for lo,hi in [(200,300),(450,600),(600,700),(700,800),(800,900),(900,1100)]:
    s=d[(d.period>=lo)&(d.period<hi)];o=[]
    for nm,e0,e1 in G:
        x=s[(s.eccentricity>=e0)&(s.eccentricity<e1)]
        b=[rat(x.iloc[rng.integers(0,len(x),len(x))]) for _ in range(200)]
        o.append('%s r=%.3f±%.3f A=%+.3f N=%d med_sigma+ %.4f - %.4f'%(nm,rat(x),np.nanstd(b),x.sense.mean(),len(x),x[x.sense>0].parallax_error.median(),x[x.sense<0].parallax_error.median()))
    print(lo,hi);print('   '+'\n   '.join(o))
# held-out only for the key cell, and G<16 check
ho=d[~hd.is_dev(d.source_id.values)];de=d[hd.is_dev(d.source_id.values)]
for nm,x in [('held',ho),('dev',de)]:
    a,b=x[(x.period>=650)&(x.period<850)&(x.eccentricity<5e-4)],x[(x.period>=650)&(x.period<850)&(x.eccentricity>=5e-4)&(x.eccentricity<.05)]
    print(nm,'650-850 pseudo r=%.3f N=%d A=%+.3f | 5e-4..0.05 r=%.3f N=%d A=%+.3f'%(rat(a),len(a),a.sense.mean(),rat(b),len(b),b.sense.mean()))
