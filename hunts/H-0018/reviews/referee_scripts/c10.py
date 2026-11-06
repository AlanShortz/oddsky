import numpy as np, pandas as pd, sys
from scipy import stats
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
from nss_rv_test import load
d=pd.concat([load(False),load(True)]);d=d[(d.nss_solution_type=='Orbital')&(d.period>=600)&(d.period<900)]
rf=d[d.sense<0].groupby(pd.cut(d[d.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median();d['m']=d.parallax/pd.cut(d.phot_g_mean_mag,np.arange(5,20)).map(rf).astype(float)*d.period/20000
d['r']=d.astrometric_excess_noise/d.a0
for lab,mk in [('G<13 m<1.5',(d.phot_g_mean_mag<13)&(d.m<1.5)),('G>=14 m<1.5',(d.phot_g_mean_mag>=14)&(d.m<1.5)),('G<13 m>=5',(d.phot_g_mean_mag<13)&(d.m>=5)),('G>=14 m 2.5-5',(d.phot_g_mean_mag>=14)&(d.m>=2.5)&(d.m<5))]:
    x=d[mk];p,m=x[x.sense>0],x[x.sense<0];print(lab,'N',len(p),len(m),'aen/a0 med+ %.3f med- %.3f KS p=%.2g'%(p.r.median(),m.r.median(),stats.ks_2samp(p.r.dropna(),m.r.dropna()).pvalue))
