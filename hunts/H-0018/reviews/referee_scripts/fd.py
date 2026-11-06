# Fisher columns: analytic vs finite-difference; normal-equation vs QR parallax sigma; psi mirror test
import numpy as np, sys
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import chiral_sim as cs, handedness as hd
from astropy.coordinates import get_body_barycentric
from astropy.time import Time
import pandas as pd
rng=np.random.default_rng(2)
scan=cs.Scan()
p=pd.read_csv(hd.NSS_CSV,usecols=['ra','dec','parallax','phot_g_mean_mag']).sample(40,random_state=9)
T0=cs.T0_JD
out=[];mirror=[];
def design(t,psi,a,d,P,e,ph,A,B,F,G,tc,psi_sign=1):
    sp,cp=np.sin(np.radians(psi_sign*psi)),np.cos(np.radians(psi_sign*psi))
    ep=get_body_barycentric('earth',Time(t+T0,format='jd',scale='tdb')).xyz.to_value('au')
    pa=ep[0]*np.sin(a)-ep[1]*np.cos(a);pd_=ep[0]*np.cos(a)*np.sin(d)+ep[1]*np.sin(a)*np.sin(d)-ep[2]*np.cos(d);fpl=pa*sp+pd_*cp
    tau=(t-tc)/365.25
    def sig(P_,e_,ph_):
        M=(2*np.pi*(t-tc)/P_+ph_)%(2*np.pi);E=cs.kepler(M,e_);X=np.cos(E)-e_;Y=np.sqrt(1-e_**2)*np.sin(E)
        return cp*(A*X+F*Y)+sp*(B*X+G*Y),X,Y
    s,X,Y=sig(P,e,ph)
    M=(2*np.pi*(t-tc)/P+ph)%(2*np.pi);E=cs.kepler(M,e);sn,cs_=np.sin(E),np.cos(E);q=np.sqrt(1-e**2);dEdM=1/(1-e*cs_)
    dX_dM,dY_dM=-sn*dEdM,q*cs_*dEdM;dEde=sn*dEdM;dX_de,dY_de=-sn*dEde-1,-e/q*sn+q*cs_*dEde
    tt=2*np.pi*(t-tc)/365.25
    dM=cp*(A*dX_dM+F*dY_dM)+sp*(B*dX_dM+G*dY_dM)
    col_T,col_nu,col_e=dM,dM*tt,cp*(A*dX_de+F*dY_de)+sp*(B*dX_de+G*dY_de)
    # finite differences
    h=1e-6
    fd_ph=(sig(P,e,ph+h)[0]-sig(P,e,ph-h)[0])/(2*h)
    nu=365.25/P;fd_nu=(sig(365.25/(nu+h),e,ph)[0]-sig(365.25/(nu-h),e,ph)[0])/(2*h)
    fd_e=(sig(P,e+h,ph)[0]-sig(P,e-h,ph)[0])/(2*h)
    Dm=np.column_stack([sp,cp,fpl,tau*sp,tau*cp,cp*X,sp*X,cp*Y,sp*Y,col_T,col_nu,col_e])
    return Dm,(col_T,fd_ph),(col_nu,fd_nu),(col_e,fd_e)
errs=[]
rat_ne=[];rat_qr=[];rat_m=[];sign=[]
for s in p.itertuples():
    t,psi=scan.transits(s.ra,s.dec)
    if len(t)<25: continue
    tc=.5*(scan.t.min()+scan.t.max());a,d=np.radians(s.ra),np.radians(s.dec)
    for _ in range(40):
        P=rng.uniform(300,900);e=rng.uniform(0.02,.6);ph=rng.uniform(0,2*np.pi)
        om,Om=rng.uniform(0,2*np.pi,2);ci=rng.uniform(-1,1)
        A=np.cos(om)*np.cos(Om)-np.sin(om)*np.sin(Om)*ci;B=np.cos(om)*np.sin(Om)+np.sin(om)*np.cos(Om)*ci;F=-np.sin(om)*np.cos(Om)-np.cos(om)*np.sin(Om)*ci;G=-np.sin(om)*np.sin(Om)+np.cos(om)*np.cos(Om)*ci
        D1,c1,c2,c3=design(t,psi,a,d,P,e,ph,A,B,F,G,tc)
        D2,*_=design(t,psi,a,d,P,e,ph,A,B,-F,-G,tc)
        for cc in (c1,c2,c3): errs.append(np.max(np.abs(cc[0]-cc[1]))/max(np.max(np.abs(cc[1])),1e-9))
        def sp_ne(Dm):
            N=Dm.T@Dm;sc=np.sqrt(np.diag(N));C=N/np.outer(sc,sc);return np.sqrt(np.linalg.inv(C)[2,2])/sc[2]
        def sp_qr(Dm):
            sc=np.linalg.norm(Dm,axis=0);Q,R_=np.linalg.qr(Dm/sc);Ri=np.linalg.inv(R_);return np.linalg.norm(Ri[2,:])/sc[2]
        rat_ne.append(sp_ne(D1)/sp_ne(D2));rat_qr.append(sp_qr(D1)/sp_qr(D2))
        sign.append(np.sign(B*F-A*G)*np.sign(s.dec))
errs=np.array(errs)
print('analytic vs FD columns: median rel err %.2e, 99%% %.2e, max %.2e'%(np.median(errs),np.percentile(errs,99),errs.max()))
print('ratio normal-eq vs QR: max rel diff %.2e'%np.max(np.abs(np.array(rat_ne)/np.array(rat_qr)-1)))
# Span identity: with T,P,e removed the 9-col span is identical under F,G -> -F,-G
print('9-col span identity: columns cpX,spX,cpY,spY do not contain F,G; ratio is exactly 1 by construction.')
