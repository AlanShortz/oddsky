import numpy as np, pandas as pd
ex=pd.read_parquet('/tmp/h7ref/ex.parquet'); t=ex[ex.sep<3]
e=t[t.visit==16].sort_values('mjd')
b1,b2=11.126,11.219
tt=e.mjd.values; m1=e.w1mpro.values; m2=e.w2mpro.values
s1=np.hypot(e.w1sigmpro.values,0.01); s2=np.hypot(e.w2sigmpro.values,0.01)
def A(u): return (u*u+2)/(u*np.sqrt(u*u+4))
rng=np.random.default_rng(1)
N=4_000_000
logtE=rng.uniform(np.log10(3),np.log10(1000),N); tE=10**logtE
u0=rng.uniform(0,0.4,N); t0=57993.05+rng.uniform(-1,1,N)*np.minimum(3*tE,400)
def Aat(T): u=np.sqrt(u0**2+((T-t0)/tE)**2); return A(u)
chi=np.zeros(N)
for T,a,b,s,ss in zip(tt,m1,m2,s1,s2):
    mA=-2.5*np.log10(Aat(T)); chi+=((b1+mA-a)/s)**2+((b2+mA-b)/ss)**2
# adjacent NEOWISE visits flat: visit medians within 0.03 mag of baseline (Feb 2017, Feb 2018); ZTF starts 2018-03
for T in [57794.4,58151.5]:
    chi+=((-2.5*np.log10(Aat(T)))/0.015)**2
w=np.exp(-0.5*(chi-chi.min()))
print('chi2 min %.1f for %d points'%(chi.min(),2*len(tt)+2))
k=w>1e-4; print('weighted samples',k.sum())
def wq(x,q): 
    i=np.argsort(x[k]); c=np.cumsum(w[k][i]); c/=c[-1]; return np.interp(q,c,x[k][i])
print('tE posterior (flat log prior) 2.5/16/50/84/97.5%:',np.round([wq(tE,q) for q in [.025,.16,.5,.84,.975]],1))
print('t0 - 57993:',np.round([wq(t0-57993.05,q) for q in [.025,.16,.5,.84,.975]],1))
print('u0:',np.round([wq(u0,q) for q in [.025,.5,.975]],3))
gaia={'Jul27':57961.74,'Aug22':57987.23,'Sep18':58014.69}
for k_,T in gaia.items():
    dm=-2.5*np.log10(Aat(T))
    print(k_,'dG median %.2f, 16-84%% [%.2f,%.2f]; P(dG<=-1.0)=%.2f, P(dG<=-0.5)=%.2f'%(wq(dm,.5),wq(dm,.16),wq(dm,.84),w[k][dm[k]<=-1].sum()/w[k].sum(),w[k][dm[k]<=-0.5].sum()/w[k].sum()))
dmax=np.minimum.reduce([-2.5*np.log10(Aat(T)) for T in gaia.values()])
print('brightest of the Gaia epochs: P(dG<=-1)=%.2f P(<=-0.75)=%.2f P(<=-0.5)=%.2f'%tuple(w[k][dmax[k]<=x].sum()/w[k].sum() for x in (-1,-.75,-.5)))
# with an astrophysical prior on tE (anticentre, lognormal median 40 d, sigma 0.35 dex)
pr=np.exp(-0.5*((logtE-np.log10(40))/0.35)**2); w2=w*pr
print('with lognormal tE prior (40 d): P(any Gaia epoch dG<=-1)=%.2f, <=-0.5: %.2f'%(w2[dmax<=-1].sum()/w2.sum(),w2[dmax<=-0.5].sum()/w2.sum()))
# ATLAS-like daily coverage: fraction of time A>1.5 from Aug 1 to Oct 31
