import numpy as np, pandas as pd, os, sys
from scipy import stats
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd
from nss_rv_test import load
R=hd.RUNS
pd.set_option('display.width',220)
a=pd.concat([load(False),load(True)]);a=a[a.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])].copy()
ah=a[~hd.is_dev(a.source_id.values)]
def Af(s): 
    m=s.sense.mean(); return m,np.sqrt((1-m*m)/max(len(s),1)),len(s)
def fmt(s): return '%+.3f±%.3f(%d)'%Af(s) if len(s)>=20 else ' -- (%d)'%len(s)
F=pd.read_parquet(f'{R}/sim_field2.parquet')
print('sim_field2 N',len(F),'acc',F.acc_plus.sum(),F.acc_minus.sum())
def Am(x): 
    n1,n2=x.acc_plus.sum(),x.acc_minus.sum();return (n1-n2)/max(n1+n2,1),n1+n2
ebins=[0,.1,.2,.3,.4,.5,.6,.7,.8,.9]
print('\n=== A vs e, P 600-900: model (field2) vs data (Orbital+SB1)')
D=a[(a.period>=600)&(a.period<900)];M=F[(F.P>=600)&(F.P<900)]
tot=[]
for e0,e1 in zip(ebins[:-1],ebins[1:]):
    x=M[(M.ecc>=e0)&(M.ecc<e1)];y=D[(D.eccentricity>=e0)&(D.eccentricity<e1)]
    Amm,n=Am(x);tot.append((Amm,len(y),n))
    print(' e[%.1f,%.1f) model A=%+.3f (Nacc=%d frac %.3f) data %s frac %.3f'%(e0,e1,Amm,n,n/(M.acc_plus.sum()+M.acc_minus.sum()),fmt(y),len(y)/len(D)))
t=np.array(tot);print(' model A overall %.3f ; reweighted to data e-dist %.3f ; data %.3f'%(Am(M)[0],np.average(t[:,0],weights=t[:,1]),D.sense.mean()))
# Reweighted jointly by e and margin
def margin_model(f): return f.plx/f.s_plx_minus*f.P/20000
M=M.assign(m=margin_model(M))
z=D.copy();ref=z[z.sense<0].groupby(pd.cut(z[z.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median()
z['m']=z.parallax/pd.cut(z.phot_g_mean_mag,np.arange(5,20)).map(ref).astype(float)*z.period/20000
mb=[0,1.5,2.5,5,10,1e9];eb=[0,.2,.4,.6,.9001]
w=0;s=0;print(' joint model/data grid (rows margin, cols e bin): model A | data A')
for l,h in zip(mb[:-1],mb[1:]):
    row=[]
    for e0,e1 in zip(eb[:-1],eb[1:]):
        x=M[(M.m>=l)&(M.m<h)&(M.ecc>=e0)&(M.ecc<e1)];y=z[(z.m>=l)&(z.m<h)&(z.eccentricity>=e0)&(z.eccentricity<e1)]
        am,n=Am(x)
        if n>0: s+=am*len(y);w+=len(y)
        row.append('%+.3f|%+.3f'%(am,y.sense.mean()))
    print('  ',l,h,row)
print(' model A reweighted to the data joint (margin, e): %.3f ; data %.3f'%(s/w,z.sense.mean()))
# by period with e-reweight only for all bins
print('\n=== by period: model, model e-reweighted, model margin+e reweighted; data')
edges=[150,200,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600,3000]
def mar_data(zz):
    zz=zz.copy();ref=zz[zz.sense<0].groupby(pd.cut(zz[zz.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median()
    zz['m']=zz.parallax/pd.cut(zz.phot_g_mean_mag,np.arange(5,20)).map(ref).astype(float)*zz.period/20000;return zz
for lo,hi in zip(edges[:-1],edges[1:]):
    Mx=F[(F.P>=lo)&(F.P<hi)];Mx=Mx.assign(m=margin_model(Mx));Dx=mar_data(a[(a.period>=lo)&(a.period<hi)])
    s1=w1=s2=w2=0
    for e0,e1 in zip(eb[:-1],eb[1:]):
        am,_=Am(Mx[(Mx.ecc>=e0)&(Mx.ecc<e1)]);n=((Dx.eccentricity>=e0)&(Dx.eccentricity<e1)).sum();s1+=am*n;w1+=n
        for l,h in zip(mb[:-1],mb[1:]):
            am,nn=Am(Mx[(Mx.ecc>=e0)&(Mx.ecc<e1)&(Mx.m>=l)&(Mx.m<h)]);n=((Dx.eccentricity>=e0)&(Dx.eccentricity<e1)&(Dx.m>=l)&(Dx.m<h)).sum()
            if nn>0: s2+=am*n;w2+=n
    print(' %4d-%4d model %+.3f  e-rw %+.3f  e+m-rw %+.3f  data %s'%(lo,hi,Am(Mx)[0],s1/w1,s2/max(w2,1),fmt(Dx)))
# A by |sin beta| model vs data
print('\n=== A by |sin beta|: model vs data; P 600-900 and 340-390')
for lo,hi in [(600,900),(300,450),(900,1600)]:
    Mx=F[(F.P>=lo)&(F.P<hi)];Dx=a[(a.period>=lo)&(a.period<hi)];r=[]
    for b0,b1 in [(0,.1),(.1,.25),(.25,.4),(.4,.55),(.55,.7),(.7,.85),(.85,1.01)]:
        m1=Am(Mx[(np.abs(np.sin(np.radians(Mx.beta)))>=b0)&(np.abs(np.sin(np.radians(Mx.beta)))<b1)])[0]
        d1=Dx[(np.abs(np.sin(np.radians(Dx.ecl_lat)))>=b0)&(np.abs(np.sin(np.radians(Dx.ecl_lat)))<b1)]
        r.append('%+.3f|%+.3f'%(m1,d1.sense.mean()))
    print(lo,hi,r)
# 76 d alias: zoom in model and data
print('\n=== short period, chirality of 63 d precession: data A in narrow bins, by |sin beta|')
for lo,hi in [(50,57),(57,63),(63,70),(70,76),(76,82),(82,90),(90,100),(100,120)]:
    x=a[(a.period>=lo)&(a.period<hi)];hb=x[np.abs(np.sin(np.radians(x.ecl_lat)))>=.7];lb=x[np.abs(np.sin(np.radians(x.ecl_lat)))<.7]
    print(' %d-%d all %s | |sinb|>=.7 %s | <.7 %s | model %+.3f (N=%d)'%(lo,hi,fmt(x),fmt(hb),fmt(lb),*Am(F[(F.P>=lo)&(F.P<hi)])))
# Model-free channel using model's ratio distribution (cond on acc_minus), data margins
print('\n=== Channel with the model ratio distribution applied to observed -NEP orbits (Orbital). P, Aobs, A_channel_medianratio-based, A_channel_modelratio')
O=a[a.nss_solution_type=='Orbital'];N_=pd.read_parquet(f'{R}/sim_nss.parquet')
N_=pd.concat([N_,F[F.G<17]]) 
rng=np.random.default_rng(3)
for lo,hi in [(50,100),(150,200),(200,300),(300,340),(340,390),(390,450),(450,500),(500,600),(600,700),(700,800),(800,900),(900,1000),(1000,1100),(1100,1300),(1300,1600),(1600,3000)]:
    x=O[(O.period>=lo)&(O.period<hi)];p,m=x[x.sense>0],x[x.sense<0]
    s=N_[(N_.P>=lo)&(N_.P<hi)&N_.acc_minus];r=(s.s_plx_plus/s.s_plx_minus).dropna().values
    mg=(m.parallax/m.parallax_error*m.period/20000).values
    if len(r)<20: continue
    rs=rng.choice(r,(50,len(mg)));surv=(mg[None,:]/rs>=1).mean()
    N_pred=len(m)*surv
    # also a0 route
    ra=(s.s_a0_plus/s.s_a0_minus).dropna().values
    sa=(m.significance*np.sqrt(m.period)/158).values
    surv2=(sa[None,:]/rng.choice(ra,(50,len(sa)))>=1).mean()
    print(' %4d-%4d Aobs %+.3f  model ratio p50 %.2f p90 %.2f  A_channel(plx) %+.3f A_channel(plx*a0) %+.3f'%(lo,hi,x.sense.mean(),np.median(r),np.percentile(r,90),(surv-1)/(surv+1),(surv*surv2-1)/(surv*surv2+1)))
# T4 3 comps
print('\n=== T4 full, held-out: D with nuisance sign(beta) x period, then x |sin beta| bins')
a2=ah.copy();a2[['nx','ny','nz']]=hd.gal_vectors(a2.ra.values,a2.dec.values)
def fit(X,y):
    b=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@b;Xi=np.linalg.pinv(X.T@X);c=Xi@((X*r[:,None]).T@(X*r[:,None]))@Xi;return b,np.sqrt(np.diag(c))
pb=np.digitize(a2.period.values,[150,200,300,340,390,450,600,900]);sg=np.sign(a2.ecl_lat.values)
n=a2[['nx','ny','nz']].values
nu=[(pb==k)*sg for k in np.unique(pb)]
b,se=fit(np.column_stack([np.ones(len(a2)),n,*nu]),a2.y.values);print(' period nuisance: D=(%.2f±%.2f,%.2f±%.2f,%.2f±%.2f)%% m=%.2f±%.2f'%(100*b[1],100*se[1],100*b[2],100*se[2],100*b[3],100*se[3],100*b[0],100*se[0]))
ab=np.abs(np.sin(np.radians(a2.ecl_lat.values)));bb=np.digitize(ab,[.1,.25,.4,.55,.7,.85])
nu2=[((pb==k)&(bb==j))*sg for k in np.unique(pb) for j in np.unique(bb)]
b,se=fit(np.column_stack([np.ones(len(a2)),n,*nu2]),a2.y.values);print(' period x |sinbeta| nuisance (%d): D=(%.2f±%.2f,%.2f±%.2f,%.2f±%.2f)%%'%(len(nu2),100*b[1],100*se[1],100*b[2],100*se[2],100*b[3],100*se[3]))
# Fit yhat from period x beta terms; predicted dipole direction with real sky
yh=np.zeros(len(a2))
for k in np.unique(pb):
    for j in np.unique(bb):
        q=(pb==k)&(bb==j);yh[q]=(a2.sense.values[q].mean())*sg[q]
f=hd.fit_dipole(yh,n);print(' pure ecliptic pattern with A(P,|sinb|): D=(%.2f,%.2f,%.2f)%% ang to -NEP %.1f'%(100*f['Dx'],100*f['Dy'],100*f['Dz'],180-f['ang_to_nep']))
# sb1 margin
print('\n=== e-table held-out vs all, variants')
for lab,dd in [('heldout',ah),('all',a)]:
    q=dd[(dd.period>=700)&(dd.period<745)&(dd.nss_solution_type=='Orbital')&(dd.phot_g_mean_mag>=12)&(dd.phot_g_mean_mag<16)];o=[];o2=[]
    for e0,e1 in [(0,.2),(.2,.4),(.4,.6),(.6,1.0)]:
        x=q[(q.eccentricity>=e0)&(q.eccentricity<e1)];rr=[]
        for g in range(12,16):
            pg,mg=x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense>0)],x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense<0)]
            if min(len(pg),len(mg))>=10: rr.append((pg.parallax_error.median()/mg.parallax_error.median(),len(pg)+len(mg)))
        o.append(round(float(np.average([v[0] for v in rr],weights=[v[1] for v in rr])),3))
        o2.append(round(float(x[x.sense>0].parallax_error.median()/x[x.sense<0].parallax_error.median()),3))
    print(' ',lab,'G-binned',o,'no G-bin',o2)
    q=dd[(dd.period>=700)&(dd.period<745)&(dd.nss_solution_type=='Orbital')];o3=[]
    for e0,e1 in [(0,.2),(.2,.4),(.4,.6),(.6,1.0)]:
        x=q[(q.eccentricity>=e0)&(q.eccentricity<e1)];o3.append(round(float(x[x.sense>0].parallax_error.median()/x[x.sense<0].parallax_error.median()),3))
    print('    all G no bin',o3)
# DR4 forecast statistic in model, proper definition
print('\n=== DR4 model values with forecast statistic (own-sense selection, G-binned) vs what forecast cites (either-sense acc)')
for nm in ['sim_dr4_nss','sim_dr4_field','sim_nss','sim_field2']:
    X=pd.read_parquet(f'{R}/{nm}.parquet')
    out=[]
    for lo,hi in [(340,390),(700,800),(600,700),(800,900),(1100,1600)]:
        b=X[(X.P>=lo)&(X.P<hi)&(X.G>=12)&(X.G<16)];rr=[]
        for g in range(12,16):
            x=b[(b.G>=g)&(b.G<g+1)];p,m=x[x.acc_plus],x[x.acc_minus]
            if min(len(p),len(m))>=10: rr.append((np.nanmedian(p.s_plx_plus)/np.nanmedian(m.s_plx_minus),len(p)+len(m)))
        cond=np.average([v[0] for v in rr],weights=[v[1] for v in rr]) if rr else np.nan
        e=b[b.acc_plus|b.acc_minus];al=np.nanmedian(e.s_plx_plus)/np.nanmedian(e.s_plx_minus)
        n=(X[(X.P>=lo)&(X.P<hi)].acc_plus.sum()-X[(X.P>=lo)&(X.P<hi)].acc_minus.sum())/max(X[(X.P>=lo)&(X.P<hi)].acc_plus.sum()+X[(X.P>=lo)&(X.P<hi)].acc_minus.sum(),1)
        out.append('%d-%d cond %.3f either %.3f A %+.3f'%(lo,hi,cond,al,n))
    print(nm,len(X),' ; '.join(out))
