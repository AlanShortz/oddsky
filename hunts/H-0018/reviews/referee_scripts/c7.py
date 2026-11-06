import numpy as np, pandas as pd, os, sys
from scipy import stats
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd, wb
from nss_rv_test import load
R=hd.RUNS
a=pd.concat([load(False),load(True)]);a=a[a.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])].copy()
O=a[a.nss_solution_type=='Orbital'].copy()
O['mp']=O.parallax/O.parallax_error*O.period/20000
O['ma']=O.significance*np.sqrt(O.period)/158
F=pd.read_parquet(f'{R}/sim_field2.parquet');Nn=pd.read_parquet(f'{R}/sim_nss.parquet')
S=pd.concat([F[(F.G>=8)&(F.G<17)],Nn[(Nn.G>=8)&(Nn.G<17)]])
rng=np.random.default_rng(7)
def sym(x,s,use_a=False):
    # identity: N+ (1-L+) = N- (1-L-); L- = P(margin-/r <1 | -), L+ = P(margin+ * r <1 | +)
    p,m=x[x.sense>0],x[x.sense<0]
    sm,sp=s[s.acc_minus],s[s.acc_plus]
    rm=(sm.s_plx_plus/sm.s_plx_minus).dropna().values;rp=(sp.s_plx_plus/sp.s_plx_minus).dropna().values
    if min(len(rm),len(rp))<25 or min(len(p),len(m))<10: return np.nan
    Sm=(m.mp.values[None,:]/rng.choice(rm,(40,len(m)))>=1).mean();Sp=(p.mp.values[None,:]*rng.choice(rp,(40,len(p)))>=1).mean()
    if use_a:
        ram=(sm.s_a0_plus/sm.s_a0_minus).dropna().values;rap=(sp.s_a0_plus/sp.s_a0_minus).dropna().values
        Sm*=(m.ma.values[None,:]/rng.choice(ram,(40,len(m)))>=1).mean();Sp*=(p.ma.values[None,:]*rng.choice(rap,(40,len(p)))>=1).mean()
    rr=Sm/Sp  # N+/N-
    return (rr-1)/(rr+1)
edges=[50,100,150,200,250,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600,3000]
print('symmetric channel estimator, Orbital, all data. columns: Aobs(se), Aplx, Aplx+a0, frozen A_model, field2 A')
print(' (also conditioned on e bin and |sinb| bin: Aplx|e,b)')
ebins=[0,.2,.4,.6,1.0];bb=[0,.25,.55,.85,1.01]
rows=[]
for lo,hi in zip(edges[:-1],edges[1:]):
    x=O[(O.period>=lo)&(O.period<hi)];s=S[(S.P>=lo)&(S.P<hi)]
    A0=x.sense.mean();se=np.sqrt((1-A0**2)/len(x))
    A1=sym(x,s);A2=sym(x,s,True)
    # conditioned
    nP=nM=0
    for e0,e1 in zip(ebins[:-1],ebins[1:]):
        for b0,b1 in zip(bb[:-1],bb[1:]):
            xx=x[(x.eccentricity>=e0)&(x.eccentricity<e1)&(np.abs(np.sin(np.radians(x.ecl_lat)))>=b0)&(np.abs(np.sin(np.radians(x.ecl_lat)))<b1)]
            ss=s[(s.ecc>=e0)&(s.ecc<e1)&(np.abs(np.sin(np.radians(s.beta)))>=b0)&(np.abs(np.sin(np.radians(s.beta)))<b1)]
            v=sym(xx,ss)
            if np.isfinite(v):
                rr=(1+v)/(1-v);n=len(xx);nM+=n/(1+rr);nP+=n*rr/(1+rr)
    Ac=(nP-nM)/(nP+nM) if nP+nM>0 else np.nan
    Am=(F[(F.P>=lo)&(F.P<hi)].acc_plus.sum()-F[(F.P>=lo)&(F.P<hi)].acc_minus.sum())/max(F[(F.P>=lo)&(F.P<hi)].acc_plus.sum()+F[(F.P>=lo)&(F.P<hi)].acc_minus.sum(),1)
    rows.append((lo,hi,A0,se,A1,A2,Ac,Am,len(x)))
    print(' %4d-%4d Aobs %+.3f±%.3f  Aplx %+.3f  Aplx+a0 %+.3f  Aplx|e,b %+.3f  field2 %+.3f  N=%d'%(lo,hi,A0,se,A1,A2,Ac,Am,len(x)))
r=np.array(rows)
k=np.isfinite(r[:,4])
print('corr Aobs vs Aplx %.3f, Aobs vs field2 %.3f ; N-wt mean residual Aobs-Aplx 300-1000: %+.3f; Aobs-Aplx|e,b %+.3f'%(np.corrcoef(r[k,2],r[k,4])[0,1],np.corrcoef(r[:,2],r[:,7])[0,1],np.average((r[:,2]-r[:,4])[(r[:,0]>=300)&(r[:,1]<=1000)],weights=r[(r[:,0]>=300)&(r[:,1]<=1000),8]),np.average((r[:,2]-r[:,6])[(r[:,0]>=300)&(r[:,1]<=1000)],weights=r[(r[:,0]>=300)&(r[:,1]<=1000),8])))
# A by e predicted, 600-900
print('\nA vs e, P 600-900 Orbital: Aobs | Aplx with model r conditioned on that e')
z=O[(O.period>=600)&(O.period<900)];sz=S[(S.P>=600)&(S.P<900)]
for e0,e1 in [(0,.1),(.1,.2),(.2,.3),(.3,.4),(.4,.5),(.5,.6),(.6,.7),(.7,.8),(.8,1.)]:
    x=z[(z.eccentricity>=e0)&(z.eccentricity<e1)];s=sz[(sz.ecc>=e0)&(sz.ecc<e1)]
    print(' e[%.1f,%.1f) Aobs %+.3f±%.3f Aplx %+.3f Aplx+a0 %+.3f  N=%d median r(accm)=%.2f'%(e0,e1,x.sense.mean(),np.sqrt((1-x.sense.mean()**2)/len(x)),sym(x,s),sym(x,s,True),len(x),np.nanmedian((s[s.acc_minus].s_plx_plus/s[s.acc_minus].s_plx_minus))))
print('\nA vs |sinb|, P 600-900 Orbital')
for b0,b1 in [(0,.1),(.1,.25),(.25,.4),(.4,.55),(.55,.7),(.7,.85),(.85,1.01)]:
    sb=np.abs(np.sin(np.radians(z.ecl_lat)));sbs=np.abs(np.sin(np.radians(sz.beta)))
    x=z[(sb>=b0)&(sb<b1)];s=sz[(sbs>=b0)&(sbs<b1)]
    print(' [%.2f,%.2f) Aobs %+.3f±%.3f Aplx %+.3f share m<1.5 %.3f'%(b0,b1,x.sense.mean(),np.sqrt((1-x.sense.mean()**2)/len(x)),sym(x,s),(x.mp<1.5).mean()))
print('\nP>1100: A by a0-margin and plx-margin, Orbital')
y=O[O.period>=1100]
for l,h in [(1,1.5),(1.5,2),(2,3),(3,5),(5,1e9)]:
    q=y[(y.ma>=l)&(y.ma<h)];print(' ma[%g,%.3g) A %+.3f±%.3f N=%d | mp>=? median mp %.1f'%(l,h,q.sense.mean(),np.sqrt((1-q.sense.mean()**2)/len(q)),len(q),q.mp.median()))
for l,h in [(1,1.5),(1.5,2),(2,3),(3,5),(5,10),(10,1e9)]:
    q=y[(y.mp>=l)&(y.mp<h)];print(' mp[%g,%.3g) A %+.3f±%.3f N=%d'%(l,h,q.sense.mean(),np.sqrt((1-q.sense.mean()**2)/len(q)),len(q)))
print(' min plx/err in Orbital by period:',[(p0,round(float((O[(O.period>=p0)&(O.period<p1)].parallax/O[(O.period>=p0)&(O.period<p1)].parallax_error).min()),1),round(20000/p1,1)) for p0,p1 in [(900,1100),(1100,1300),(1300,1600),(1600,2000),(2000,3000)]])
print('\nFaint fake test: G>=15, low margin mp<1.5 by m_ref? KS by sense, Orbital P 600-900')
fz=z[(z.phot_g_mean_mag>=15)];
ref=z[z.sense<0].groupby(pd.cut(z[z.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median()
fz=fz.assign(m_ref=fz.parallax/pd.cut(fz.phot_g_mean_mag,np.arange(5,20)).map(ref).astype(float)*fz.period/20000)
l=fz[fz.m_ref<1.5];p,m=l[l.sense>0],l[l.sense<0]
print(' N+',len(p),'N-',len(m),'A',round(l.sense.mean(),3))
for c in ['mf','a0_au','significance','goodness_of_fit','ruwe','bp_rp','phot_g_mean_mag','parallax','eccentricity','visibility_periods_used']:
    print('   %-20s med+ %.3f med- %.3f KS p=%.2g'%(c,p[c].median(),m[c].median(),stats.ks_2samp(p[c].dropna(),m[c].dropna()).pvalue))
print(' fraction mf>0.3: +%.3f -%.3f'%((p.mf>.3).mean(),(m.mf>.3).mean()))
print(' Are low-e -NEP at G>=15 like low-e +NEP? low-e (e<.3): mf KS p=%.2g, significance KS p=%.2g, N %d %d'%(stats.ks_2samp(p[p.eccentricity<.3].mf,m[m.eccentricity<.3].mf).pvalue,stats.ks_2samp(p[p.eccentricity<.3].significance,m[m.eccentricity<.3].significance).pvalue,(p.eccentricity<.3).sum(),(m.eccentricity<.3).sum()))
print(' HRD check: absolute G by colour; median M_G offset from main sequence not computed; M_G med+ %.2f med- %.2f; KS p=%.2g'%((p.phot_g_mean_mag+5*np.log10(p.parallax/100)).median(),(m.phot_g_mean_mag+5*np.log10(m.parallax/100)).median(),stats.ks_2samp(p.phot_g_mean_mag+5*np.log10(p.parallax/100),m.phot_g_mean_mag+5*np.log10(m.parallax/100)).pvalue))
print(' DR3 retention test impossible; period precision: period_error/period by sense: med+ %.4f med- %.4f; parallax_over_error gaia_source vs nss ratio: med+ %.3f med- %.3f'%((p.period_error/p.period).median(),(m.period_error/m.period).median(),((p.parallax/p.parallax_error)/p.parallax_over_error).median(),((m.parallax/m.parallax_error)/m.parallax_over_error).median()))
# one-year: A by e (Butkevich: no effect at e>=0.5)
print('\n340-390 and 300-450 A by e')
for lo,hi in [(340,390),(300,450)]:
    q=a[(a.period>=lo)&(a.period<hi)]
    print(lo,hi,[(e0,round(q[(q.eccentricity>=e0)&(q.eccentricity<e1)].sense.mean(),3),int(((q.eccentricity>=e0)&(q.eccentricity<e1)).sum())) for e0,e1 in [(0,.2),(.2,.4),(.4,.6),(.6,1)]])
# T2 with non noisy model
he=pd.read_csv('/Users/alanshortz/conductor/workspaces/oddsky/edmonton/hunts/H-0018/work/nss_by_period_heldout.csv')
e=[]
for lo,hi in zip(he.lo,he.hi):
    x=F[(F.P>=lo)&(F.P<hi)];e.append((x.acc_plus.sum()-x.acc_minus.sum())/max(x.acc_plus.sum()+x.acc_minus.sum(),1))
print('\nT2 rho with bigger sim_field2 (not frozen): %.3f ; frozen %.3f; N_model range %d-%d'%(stats.spearmanr(he.A,e).statistic,stats.spearmanr(he.A,he.A_model).statistic,1,1), ' A_model se at 340-390 ~ %.3f; 50-100 ~ %.3f; 150-200 ~ %.3f'%(1/np.sqrt(108),1/np.sqrt(167),1/np.sqrt(429)))
print(' Model zone 150-200 field2 %.3f; 50-100 field2 %.3f'%(e[2],e[0]))
# WB spin
print('\nWB spin term S')
path=f'{R}/data/elbadry/cat.parquet'
d=wb.load(path,True);z_,s_,n_=wb.rotation(d);sel=np.abs(z_)>3*s_
ds=d[sel];y=np.sign(z_[sel]);nn=n_[sel]
n1,n2=wb.unit(ds.ra1.values,ds.dec1.values),wb.unit(ds.ra2.values,ds.dec2.values);r=n2-n1;r/=np.linalg.norm(r,axis=1,keepdims=True)
g1,g2=ds.phot_g_mean_mag1.values,ds.phot_g_mean_mag2.values
def fit(rv,m,lab,frame='icrs'):
    X=np.column_stack([np.ones(m.sum()),nn[m],rv[m]]);b=np.linalg.lstsq(X,y[m],rcond=None)[0];res=y[m]-X@b;Xi=np.linalg.inv(X.T@X);c=Xi@((X*res[:,None]).T@(X*res[:,None]))@Xi;se=np.sqrt(np.diag(c))
    print(' %-34s N=%6d Dz=%+.2f±%.2f  S(icrs)=(%+.2f±%.2f,%+.2f±%.2f,%+.2f±%.2f)%%'%(lab,m.sum(),100*b[3],100*se[3],100*b[4],100*se[4],100*b[5],100*se[5],100*b[6],100*se[6]))
ord_=np.where(g1<g2,1.0,-1.0);rb=r*ord_[:,None]
rnd=np.where(np.random.default_rng(1).random(len(r))<.5,1.,-1.);rr=r*rnd[:,None]
allm=np.ones(len(y),bool);gmin=np.minimum(g1,g2);dG=np.abs(g1-g2)
fit(rb,allm,'bright->faint all');fit(rr,allm,'random order control')
fit(rb,(gmin>13)&(dG<1),'both>13,|dG|<1');fit(rb,(gmin<13)&(dG>=1),'bright<13,|dG|>=1');fit(rb,(gmin<13)&(np.maximum(g1,g2)>13),'straddles G=13');fit(rb,(gmin>13)&(dG>=1),'both>13,|dG|>=1');fit(rb,(gmin<13)&(np.maximum(g1,g2)<13),'both<13')
