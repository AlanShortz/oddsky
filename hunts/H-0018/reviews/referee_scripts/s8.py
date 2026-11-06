# One small check: DR4 stand-in with the final ~188 d (2019-07-16 to 2020-01-20) reversed-precession segment, built by reflecting the
# scan circles in the ecliptic plane; --stars 300. Also numeric checks of Fisher columns on a handful of stars.
import numpy as np, sys, os, pandas as pd, types
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import chiral_sim as cs, handedness as hd
from astropy.coordinates import SkyCoord, BarycentricMeanEcliptic
import astropy.units as u
from scipy.spatial import cKDTree
nep=SkyCoord(lon=0*u.deg,lat=90*u.deg,frame='barycentricmeanecliptic').icrs.cartesian.xyz.value
class S2(cs.Scan):
    def __init__(self,*a,**k):
        super().__init__(*a,**k)
        t=np.concatenate([self.t,self.t+3*365.25]);ra=np.concatenate([self.ra]*2);dec=np.concatenate([self.dec]*2);psi=np.concatenate([self.psi]*2);fov=np.concatenate([self.fov]*2)
        tmax=1666.44+2006; t0=tmax-188
        m=(t>=t0)
        v=cs.unit(ra[m],dec[m]);a_,d_=np.radians(ra[m]),np.radians(dec[m]);p=np.radians(psi[m])
        e=np.column_stack([-np.sin(a_),np.cos(a_),0*a_]);n=np.column_stack([-np.sin(d_)*np.cos(a_),-np.sin(d_)*np.sin(a_),np.cos(d_)])
        dv=np.sin(p)[:,None]*e+np.cos(p)[:,None]*n
        v2=v-2*(v@nep)[:,None]*nep;dv2=dv-2*(dv@nep)[:,None]*nep
        ra2=np.degrees(np.arctan2(v2[:,1],v2[:,0]))%360;dec2=np.degrees(np.arcsin(v2[:,2]))
        a2,d2=np.radians(ra2),np.radians(dec2);e2=np.column_stack([-np.sin(a2),np.cos(a2),0*a2]);n2=np.column_stack([-np.sin(d2)*np.cos(a2),-np.sin(d2)*np.sin(a2),np.cos(d2)])
        psi2=np.degrees(np.arctan2((dv2*e2).sum(1),(dv2*n2).sum(1)))%360
        ra[m],dec[m],psi[m]=ra2,dec2,psi2
        self.t,self.ra,self.dec,self.psi,self.fov=t,ra,dec,psi,fov
        self.tree=cKDTree(cs.unit(self.ra,self.dec))
cs.Scan=S2
args=types.SimpleNamespace(seed=181,parent='nss',stars=300,draws=100,tmax=1666.44+2006,dr4=False,fix='',out='/tmp/ref_h18/sim_dr4_rev.parquet')
d=cs.simulate(args)
X=d
ref=pd.read_parquet(f'{hd.RUNS}/sim_dr4_nss.parquet')
print('compare: bin | rev: all, either, cond, A | frozen stand-in sim_dr4_nss: all, either, cond, A')
for lo,hi in [(150,200),(340,390),(600,700),(700,800),(800,900),(1100,1600)]:
    o=[]
    for Y in (X,ref):
        b=Y[(Y.P>=lo)&(Y.P<hi)];e=b[b.acc_plus|b.acc_minus]
        c=np.nanmedian(b[b.acc_plus].s_plx_plus)/np.nanmedian(b[b.acc_minus].s_plx_minus)
        A=(b.acc_plus.sum()-b.acc_minus.sum())/max(b.acc_plus.sum()+b.acc_minus.sum(),1)
        o.append('%.3f %.3f %.3f %+.3f (N=%d)'%(np.nanmedian(b.s_plx_plus)/np.nanmedian(b.s_plx_minus),np.nanmedian(e.s_plx_plus)/np.nanmedian(e.s_plx_minus),c,A,len(b)))
    print(lo,hi,' | '.join(o))
