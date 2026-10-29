import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',50)
ex=pd.read_parquet('hunts/H-0007/work/exp_J040025.parquet')
ra,dec=60.1073758,32.5909576
# Gaia pm, propagate to each epoch from 2016.0
pmra,pmdec=-1.221,-1.585
yr=(ex.mjd-57388.5)/365.25
ra_t=ra+pmra/3.6e6*yr/np.cos(np.radians(dec)); dec_t=dec+pmdec/3.6e6*yr
ex['dra']=3600*(ex.ra-ra_t)*np.cos(np.radians(dec)); ex['ddec']=3600*(ex.dec-dec_t)
ex['sep']=np.hypot(ex.dra,ex.ddec)
ex['visit']=np.round((ex.mjd-55000)/182.6).astype(int)
t=ex[ex.sep<3].copy()
t['c']=t.w1mpro-t.w2mpro
g=t.groupby('visit').agg(t=('mjd','median'),n=('mjd','size'),w1=('w1mpro','median'),w1s=('w1mpro','std'),w2=('w2mpro','median'),w2s=('w2mpro','std'),
 c=('c','median'),cs=('c','std'),dra=('dra','mean'),ddec=('ddec','mean'),sdra=('dra','std'),r1=('w1rchi2','median'),r2=('w2rchi2','median'),
 q5=('qual_frame',lambda x:(x<10).mean()),nb=('nb','max'),na=('na','max'),sso=('sso_flg','max'),saa=('saa_sep','min'),moon=('moon_masked',lambda x:''.join(sorted(set(x)))),cc=('cc_flags',lambda x:','.join(sorted(set(x)))),ph=('ph_qual',lambda x:','.join(sorted(set(x)))))
print(g.round(3).to_string())
ev=g.loc[g.t.between(57990,57995)].index[0]
base=g.drop(ev)
print('event visit',ev)
for b in ['w1','w2','c']:
    print(b,'base median %.3f std %.3f ; event %.3f ; delta %.3f'%(base[b].median(),base[b].std(),g.loc[ev,b],g.loc[ev,b]-base[b].median()))
print('flux ratio W1 %.3f W2 %.3f'%(10**(-0.4*(g.loc[ev,'w1']-base.w1.median())),10**(-0.4*(g.loc[ev,'w2']-base.w2.median()))))
print('centroid event: dra %.3f ddec %.3f; base mean dra %.3f+-%.3f ddec %.3f+-%.3f'%(g.loc[ev,'dra'],g.loc[ev,'ddec'],base.dra.mean(),base.dra.std(),base.ddec.mean(),base.ddec.std()))
e=t[t.visit==ev]
print('event exposures centroid err of mean dra %.3f ddec %.3f'%(e.dra.std()/np.sqrt(len(e)),e.ddec.std()/np.sqrt(len(e))))
# rchi2 distribution over all target exposures
print('rchi2 W1 percentiles all non-event:',np.percentile(t[t.visit!=ev].w1rchi2,[50,90,99]).round(2),' event:',np.percentile(e.w1rchi2,[50,90]).round(2))
# slope in event
for b in ['w1mpro','w2mpro']:
    p,cov=np.polyfit(e.mjd-e.mjd.mean(),e[b],1,cov=True); print(b,'slope %.4f +- %.4f mag/d'%(p[0],np.sqrt(cov[0,0])))
pc,cc=np.polyfit(e.mjd-e.mjd.mean(),e.w1mpro-e.w2mpro,1,cov=True);print('colour slope %.4f+-%.4f'%(pc[0],np.sqrt(cc[0,0])))
ex.to_parquet('/tmp/h7ref/ex.parquet')
