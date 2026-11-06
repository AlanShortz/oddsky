import numpy as np, pandas as pd, os, sys
R=os.path.expanduser('~/oddsky-runs/h0018')
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd
from nss_rv_test import load
pd.set_option('display.width',220);pd.set_option('display.max_rows',300)
a=pd.concat([load(False),load(True)])
a=a[a.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])].copy()
a['raw']=a.parallax/a.parallax_error*a.period/20000
def A(s): 
    m=s.sense.mean(); return m,np.sqrt((1-m*m)/max(len(s),1)),len(s)
print('N+',(a.sense>0).sum(),'N-',(a.sense<0).sum(),'zero/nan',((a.sense==0)|a.sense.isna()).sum(),'A',a.sense.mean())
print('by type', {t:tuple(round(x,4) for x in A(g)) for t,g in a.groupby('nss_solution_type')})
print('\n--- A by period and type')
edges=[50,100,150,200,250,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600,3000]
for lo,hi in zip(edges[:-1],edges[1:]):
    s=a[(a.period>=lo)&(a.period<hi)]
    o,b=s[s.nss_solution_type=='Orbital'],s[s.nss_solution_type=='AstroSpectroSB1']
    print(lo,hi,'Orb %+.3f±%.3f N=%d | SB1 %+.3f±%.3f N=%d'%(*A(o),*A(b)))
# MODEL-FREE CHANNEL: take -NEP sample, inflate error by measured ratio, count who would fail
print('\n--- model-free channel: inflate -NEP sigma by the measured ratio (G,P) and apply cut; predicted A vs observed')
pb=[50,100,150,200,250,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600,3000]
gb=np.arange(5,20)
tot=[]
for ty in ['Orbital','both']:
  aa=a if ty=='both' else a[a.nss_solution_type=='Orbital']
  print(ty)
  for lo,hi in zip(pb[:-1],pb[1:]):
    s=aa[(aa.period>=lo)&(aa.period<hi)]
    p,m=s[s.sense>0],s[s.sense<0]
    keep_m=np.zeros(len(m));
    # ratio by G bin; also apply to + (deflate): symmetric estimate
    lost=0;Nm=0;gained=0;Np=0
    for g in gb:
        pg,mg=p[(p.phot_g_mean_mag>=g)&(p.phot_g_mean_mag<g+1)],m[(m.phot_g_mean_mag>=g)&(m.phot_g_mean_mag<g+1)]
        if min(len(pg),len(mg))<10:
            Nm+=len(mg);Np+=len(pg);continue
        r=np.median(pg.parallax_error)/np.median(mg.parallax_error)
        marg=mg.parallax/mg.parallax_error*mg.period/20000
        lost+=(marg<max(r,1)).sum() if r>=1 else 0
        gained+=0
        if r<1:
            # + stars lost relative to minus... the minus sense is favoured less: lost from + side reversed
            margp=pg.parallax/pg.parallax_error*pg.period/20000
            gained+=(margp<1/r).sum()
        Nm+=len(mg);Np+=len(pg)
    # predicted: N+ = Nm - lost ; or Nm = Np - gained
    Apred=(-(lost)+gained)/(2*Nm-lost+gained) if Nm else np.nan
    Aobs=(Np-Nm)/(Np+Nm)
    print(' %4d-%4d N+ %6d N- %6d Aobs %+.3f  Apred(channel only) %+.3f lost %d gained %d'%(lo,hi,Np,Nm,Aobs,Apred,lost,gained))
# A by |beta| for mechanism
print('\n--- A and ratio by |sin beta|')
for z,(lo,hi) in {'340-390':(340,390),'300-450':(300,450),'600-900':(600,900),'700-800':(700,800),'900-1600':(900,1600),'150-200':(150,200),'72-100':(72,100),'200-300':(200,300),'500-600':(500,600)}.items():
    s=a[(a.period>=lo)&(a.period<hi)]
    row=[]
    for b0,b1 in [(0,.1),(.1,.25),(.25,.4),(.4,.55),(.55,.7),(.7,.85),(.85,1.01)]:
        x=s[(np.abs(np.sin(np.radians(s.ecl_lat)))>=b0)&(np.abs(np.sin(np.radians(s.ecl_lat)))<b1)]
        o=x[(x.nss_solution_type=='Orbital')&(x.phot_g_mean_mag>=12)&(x.phot_g_mean_mag<16)]
        pm=[]
        for g in range(12,16):
            pg,mg=o[(o.phot_g_mean_mag>=g)&(o.phot_g_mean_mag<g+1)&(o.sense>0)],o[(o.phot_g_mean_mag>=g)&(o.phot_g_mean_mag<g+1)&(o.sense<0)]
            if min(len(pg),len(mg))>=8: pm.append((pg.parallax_error.median()/mg.parallax_error.median(),len(pg)+len(mg)))
        r=np.average([q[0] for q in pm],weights=[q[1] for q in pm]) if pm else np.nan
        row.append('%+.3f(%.3f,%d) r=%.2f'%(*A(x),r))
    print(z,' | '.join(row))
# North vs south
print('\n--- hemispheres: mean y by period zone, ecliptic N and S')
for lo,hi in [(340,390),(300,450),(600,900),(900,3000),(100,300)]:
    s=a[(a.period>=lo)&(a.period<hi)]
    n,so=s[s.ecl_lat>0],s[s.ecl_lat<0]
    print(lo,hi,'N: y=%+.3f±%.3f n=%d  S: y=%+.3f±%.3f n=%d'%(n.y.mean(),np.sqrt(1/len(n)),len(n),so.y.mean(),np.sqrt(1/len(so)),len(so)))
# Galactic hemispheres and longitude
print('\n--- A(600-900) by ecliptic longitude sector and Galactic latitude')
s=a[(a.period>=600)&(a.period<900)]
for l0 in range(0,360,60):
    x=s[(s.ecl_lon>=l0)&(s.ecl_lon<l0+60)]
    print(' lon',l0,'%+.3f±%.3f n=%d'%A(x))
for b0,b1 in [(-90,-30),(-30,-10),(-10,10),(10,30),(30,90)]:
    x=s[(s.b>=b0)&(s.b<b1)]
    print(' b',b0,b1,'%+.3f±%.3f n=%d'%A(x))
# Pure ecliptic pattern: predicted dipole direction with real sky
print('\n--- Would a pure sign(beta)*A(P) pattern on this sky give the 20-deg offset?')
a[['nx','ny','nz']]=hd.gal_vectors(a.ra.values,a.dec.values)
aho=a[~hd.is_dev(a.source_id.values)]
y=aho.sense.values*0
A_of=aho.groupby(pd.cut(aho.period,[0,150,200,300,340,390,450,600,900,1e9]),observed=True).sense.transform('mean').values
yhat=A_of*np.sign(aho.ecl_lat.values)
f=hd.fit_dipole(yhat,aho[['nx','ny','nz']].values)
print(' sign(beta)*A(P): D=(%.2f,%.2f,%.2f)%%, ang to -NEP %.1f'%(100*f['Dx'],100*f['Dy'],100*f['Dz'],180-f['ang_to_nep']))
f=hd.fit_dipole(aho.y.values,aho[['nx','ny','nz']].values);print(' actual y: D=(%.2f,%.2f,%.2f)%%, ang to -NEP %.1f; ang to NGP %.1f'%(100*f['Dx'],100*f['Dy'],100*f['Dz'],180-f['ang_to_nep'],f['ang_to_ngp']))
r=aho.y.values-yhat
f=hd.fit_dipole(r,aho[['nx','ny','nz']].values);print(' residual y-yhat: D=(%.2f±%.2f,%.2f±%.2f,%.2f±%.2f)%% chi2 %.1f'%(100*f['Dx'],100*f['Dx_se'],100*f['Dy'],100*f['Dy_se'],100*f['Dz'],100*f['Dz_se'],f['chi2_D']))
# 3D Lhat with correct units
s3=aho[aho.nss_solution_type=='AstroSpectroSB1'].dropna(subset=['c_thiele_innes','h_thiele_innes'])
from astropy import units as u
from astropy.coordinates import SkyCoord
def L3(s,mult):
    P=np.column_stack([s.b_thiele_innes,s.a_thiele_innes,s.c_thiele_innes*mult]);Q=np.column_stack([s.g_thiele_innes,s.f_thiele_innes,s.h_thiele_innes*mult])
    L=np.cross(P,Q);L/=np.linalg.norm(L,axis=1,keepdims=True)
    ra,dec=np.radians(s.ra.values),np.radians(s.dec.values)
    ee=np.column_stack([-np.sin(ra),np.cos(ra),0*ra]);en=np.column_stack([-np.sin(dec)*np.cos(ra),-np.sin(dec)*np.sin(ra),np.cos(dec)]);er=np.column_stack([np.cos(dec)*np.cos(ra),np.cos(dec)*np.sin(ra),np.sin(dec)])
    v=ee*L[:,[0]]+en*L[:,[1]]+er*L[:,[2]]
    return SkyCoord(x=v[:,0],y=v[:,1],z=v[:,2],representation_type='cartesian',frame='icrs').galactic.cartesian.xyz.value.T
for nm,mu in [('raw C,H (final.py)',1.0),('C,H x parallax (mas)',s3.parallax.values[:,None]*1.0)]:
    if isinstance(mu,np.ndarray): 
        s=s3.copy(); s['c_thiele_innes']=s.c_thiele_innes*s.parallax; s['h_thiele_innes']=s.h_thiele_innes*s.parallax; g=L3(s,1.0)
    else: g=L3(s3,1.0)
    m,e=g.mean(0),g.std(0)/np.sqrt(len(g))
    print(nm,'<L>=(%+.2f±%.2f,%+.2f±%.2f,%+.2f±%.2f)%% N=%d'%(100*m[0],100*e[0],100*m[1],100*e[1],100*m[2],100*e[2],len(g)), ' pred Z from Y %.2f'%(100*m[1]*0.4971/0.8623))
