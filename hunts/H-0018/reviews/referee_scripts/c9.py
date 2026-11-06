import numpy as np, pandas as pd, os, sys
from scipy import stats
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd
from nss_rv_test import load
a=load(True);a=a[a.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])].copy()
a[['nx','ny','nz']]=hd.gal_vectors(a.ra.values,a.dec.values)
n=a[['nx','ny','nz']].values
a['pb']=np.digitize(a.period,[150,200,300,340,390,450,600,900])
ref=a[a.sense<0].groupby(['pb',pd.cut(a[a.sense<0].phot_g_mean_mag,np.arange(5,20))],observed=True).parallax_error.median()
gb=pd.cut(a.phot_g_mean_mag,np.arange(5,20))
a['sig_ref']=[ref.get((p,g),np.nan) for p,g in zip(a.pb,gb)]
a['mref']=a.parallax/a.sig_ref*a.period/20000
a['mb']=np.digitize(a.mref.fillna(3),[1.5,2.5,5,10])
a['bb']=np.digitize(np.abs(a.b),[10,30])
a['sb']=np.digitize(np.abs(np.sin(np.radians(a.ecl_lat))),[.1,.25,.4,.55,.7,.85])
sg=np.sign(a.ecl_lat.values)
print('actual:',{k:round(100*v,2) for k,v in hd.fit_dipole(a.y.values,n).items() if k in('Dx','Dy','Dz')},'ang -NEP',round(180-hd.fit_dipole(a.y.values,n)['ang_to_nep'],1))
for lab,keys in [('P',['pb']),('P,|sinb_ecl|',['pb','sb']),('P,|b|',['pb','bb']),('P,margin',['pb','mb']),('P,margin,|sinb_ecl|',['pb','mb','sb']),('P,margin,|sinb_ecl|,|b|',['pb','mb','sb','bb'])]:
    Am=a.groupby(keys,observed=True).sense.transform('mean').values
    yh=Am*sg
    f=hd.fit_dipole(yh,n);r=hd.fit_dipole(a.y.values-yh,n)
    print('%-26s pattern D=(%.2f,%.2f,%.2f)%% ang-NEP %.1f | residual D=(%.2f±%.2f,%.2f±%.2f,%.2f±%.2f)%% chi2 %.1f'%(lab,100*f['Dx'],100*f['Dy'],100*f['Dz'],180-f['ang_to_nep'],100*r['Dx'],100*r['Dx_se'],100*r['Dy'],100*r['Dy_se'],100*r['Dz'],100*r['Dz_se'],r['chi2_D']))
# A by |b| at fixed margin
z=a[(a.period>=600)&(a.period<900)]
for l,h in [(0,1.5),(1.5,2.5),(2.5,5),(5,1e9)]:
    print(' margin',l,h,[ (b0,round(z[(z.mref>=l)&(z.mref<h)&(np.abs(z.b)>=b0)&(np.abs(z.b)<b1)].sense.mean(),3)) for b0,b1 in [(0,10),(10,30),(30,90)]])
print(' share m<1.5 by |b|:',[round((z[(np.abs(z.b)>=b0)&(np.abs(z.b)<b1)].mref<1.5).mean(),3) for b0,b1 in [(0,10),(10,30),(30,90)]])
# transits model vs data
s=pd.read_parquet(f'{hd.RUNS}/sim_field2.parquet',columns=['nt','G','P','s_plx_minus']);nss=pd.read_parquet(f'{hd.RUNS}/sim_nss.parquet',columns=['nt','G'])
o=load(True);o=o[o.nss_solution_type=='Orbital']
print('\ntransits: sim_nss median nt %.0f ; data matched_transits median %.0f, visibility %.0f ; ratio predicted sigma from N: sqrt=%.2f'%(nss.nt.median(),o.astrometric_matched_transits.median(),o.visibility_periods_used.median(),np.sqrt(nss.nt.median()/o.astrometric_matched_transits.median())))
# RUWE/AEN vs a0 faint low margin
f=load(False);f=pd.concat([f,o]);f=f[(f.nss_solution_type=='Orbital')&(f.period>=600)&(f.period<900)&(f.phot_g_mean_mag>=14)]
rf=f[f.sense<0].groupby(pd.cut(f[f.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median()
f['m']=f.parallax/pd.cut(f.phot_g_mean_mag,np.arange(5,20)).map(rf).astype(float)*f.period/20000
x=f[f.m<1.5]
x=x.assign(r=x.astrometric_excess_noise/x.a0)
p,m=x[x.sense>0],x[x.sense<0];print('\nfaint low margin: aen/a0 med+ %.3f med- %.3f KS p=%.3g (N %d %d)'%(p.r.median(),m.r.median(),stats.ks_2samp(p.r.dropna(),m.r.dropna()).pvalue,len(p),len(m)))
# Same at matched e<0.3
p2,m2=p[p.eccentricity<.3],m[m.eccentricity<.3];print(' e<.3 aen/a0 med+ %.3f med- %.3f KS p=%.3g (N %d %d)'%(p2.r.median(),m2.r.median(),stats.ks_2samp(p2.r.dropna(),m2.r.dropna()).pvalue,len(p2),len(m2)))
# F6 confound: margin distributions
d=pd.concat([load(False),load(True)]);d=d[(d.nss_solution_type=='Orbital')&(d.period>=600)&(d.period<900)]
rf=d[d.sense<0].groupby(pd.cut(d[d.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median();d['m']=d.parallax/pd.cut(d.phot_g_mean_mag,np.arange(5,20)).map(rf).astype(float)*d.period/20000
d['sig']=d.significance
print('\nF6 confound, Orbital 600-900: + median significance %.1f, - %.1f; share sig<15 + %.3f - %.3f; share m<1.5 + %.3f, - %.3f; excess frac 1-N+/N- %.3f'%(d[d.sense>0].sig.median(),d[d.sense<0].sig.median(),(d[d.sense>0].sig<15).mean(),(d[d.sense<0].sig<15).mean(),(d[d.sense>0].m<1.5).mean(),(d[d.sense<0].m<1.5).mean(),1-(d.sense>0).sum()/(d.sense<0).sum()))
