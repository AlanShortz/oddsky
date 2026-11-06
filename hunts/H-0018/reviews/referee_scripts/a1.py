import numpy as np, pandas as pd, os, sys
R=os.path.expanduser('~/oddsky-runs/h0018')
print(os.listdir(R+'/data'), os.listdir(R+'/data/scanlaw') if os.path.isdir(R+'/data/scanlaw') else None)
z=np.load(R+'/data/scanlaw/scan30s.npz')
t,ra,dec,psi,fov=z['t'],z['ra'],z['dec'],z['psi'],z['fov']
print('t range',t.min(),t.max(),'len',len(t),'JD',t.min()+2455197.5,t.max()+2455197.5)
m=fov==1
t1,ra1,dec1,psi1=t[m],ra[m],dec[m],psi[m]
o=np.argsort(t1);t1,ra1,dec1,psi1=t1[o],ra1[o],dec1[o],psi1[o]
dt=np.diff(t1)*86400
k=(dt>25)&(dt<35)
dE=((ra1[1:]-ra1[:-1]+180)%360-180)*np.cos(np.radians(dec1[:-1]))
dN=dec1[1:]-dec1[:-1]
head=np.degrees(np.arctan2(dE,dN))  # angle from N through E of direction of motion
dpsi=(head-psi1[:-1]+180)%360-180
s=np.abs(dec1[:-1])<70
print('heading - psi (deg) quantiles (north->east convention expects ~0):',np.nanpercentile(dpsi[k&s],[1,25,50,75,99]))
head2=np.degrees(np.arctan2(-dE,dN))
dpsi2=(head2-psi1[:-1]+180)%360-180
print('mirror convention (N->W):',np.nanpercentile(dpsi2[k&s],[1,25,50,75,99]))
print('speed arcsec/s',np.median(np.hypot(dE,dN)[k]/dt[k]*3600))
# fov2 vs fov1 separation (basic angle 106.5)
d=pd.read_csv(R+'/data/nss/nss_astrometric.csv',dtype={'source_id':'int64'})
print(d.nss_solution_type.value_counts())
ex=pd.read_csv(R+'/data/nss/nss_rv.csv',dtype={'source_id':'int64'})
print(len(d),d.source_id.nunique())
x=d.merge(ex[['source_id','parallax_over_error','astrometric_params_solved']].drop_duplicates('source_id'),on='source_id',how='left')
x['poe']=x.parallax/x.parallax_error
print('nss plx/err vs gaia_source parallax_over_error: median ratio',np.nanmedian(x.poe/x.parallax_over_error),'q',np.nanpercentile(x.poe/x.parallax_over_error,[5,25,75,95]),'frac equal 1% ',np.nanmean(np.abs(x.poe/x.parallax_over_error-1)<0.01))
print('astrometric_params_solved',x.astrometric_params_solved.value_counts(dropna=False).head())
x['m_plx']=x.poe*x.period/20000
x['m_a0']=x.significance*np.sqrt(x.period)/158
for ty,g in x.groupby('nss_solution_type'):
    print(ty,len(g),'min m_plx %.3f q1%% %.3f  frac<1 %.4f | min m_a0 %.3f q1%% %.3f frac<1 %.4f | sig min %.2f | min plxSN %.2f | ruwe min %.3f frac<1.4 %.3f'%(g.m_plx.min(),g.m_plx.quantile(.01),(g.m_plx<1).mean(),g.m_a0.min(),g.m_a0.quantile(.01),(g.m_a0<1).mean(),g.significance.min(),g.poe.min(),g.ruwe.min(),(g.ruwe<1.4).mean()))
# TI units: C,H
s=d[d.nss_solution_type=='AstroSpectroSB1'].dropna(subset=['c_thiele_innes','h_thiele_innes']).copy()
A,B,F,G,C,H=[s[c+'_thiele_innes'] for c in 'abfgch']
print('SB1 N',len(s))
na=A*F+B*G  # plane dot
for name,cc,hh in [('C,H raw',C,H),('C,H*parallax',C*s.parallax,H*s.parallax),('C,H/parallax',C/s.parallax,H/s.parallax)]:
    dot=(na+cc*hh)/np.sqrt((A**2+B**2+cc**2)*(F**2+G**2+hh**2))
    nrm=np.log10((A**2+B**2+cc**2)/(F**2+G**2+hh**2))/2
    print(name,'median |cos(P,Q)| %.4f  frac|cos|<.1 %.3f  median|log10 |P|/|Q|| %.4f'%(np.median(np.abs(dot)),(np.abs(dot)<.1).mean(),np.median(np.abs(nrm))))
print('median |A| %.3f |C| %.3f  parallax %.2f'%(np.median(np.abs(A)),np.median(np.abs(C)),s.parallax.median()))
