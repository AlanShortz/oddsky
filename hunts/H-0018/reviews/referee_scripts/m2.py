import numpy as np, pandas as pd, os, sys
from scipy import stats
R=os.path.expanduser('~/oddsky-runs/h0018')
W='/Users/alanshortz/conductor/workspaces/oddsky/edmonton/hunts/H-0018/work/'
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd
from nss_rv_test import load
dev=pd.read_csv(W+'nss_by_period_dev.csv');he=pd.read_csv(W+'nss_by_period_heldout.csv')
for n,t in [('dev',dev),('held',he)]:
    ok=t.ratio.notna()
    print(n,'T1 r %.3f med|d| %.3f  T2 rho %.3f  r(ratio)-pearson A %.3f'%(np.corrcoef(t.ratio[ok],t.ratio_model[ok])[0,1],np.median(np.abs(t.ratio[ok]-t.ratio_model[ok])),stats.spearmanr(t.A,t.A_model).statistic,np.corrcoef(t.A,t.A_model)[0,1]))
print('dev vs held ratio corr %.3f; A corr %.3f'%(np.corrcoef(dev.ratio,he.ratio)[0,1],np.corrcoef(dev.A,he.A)[0,1]))
t=he
# leave one out
loo=[(int(t.lo[i]),round(np.corrcoef(np.delete(t.ratio.values,i),np.delete(t.ratio_model.values,i))[0,1],3)) for i in range(len(t))]
print('LOO r',loo)
print('spearman ratio',round(stats.spearmanr(t.ratio,t.ratio_model).statistic,3))
# bootstrap r from ratio_se
rng=np.random.default_rng(1)
rs=[np.corrcoef(t.ratio+rng.normal(0,t.ratio_se),t.ratio_model)[0,1] for _ in range(4000)]
print('r with data noise: mean %.3f 16-84 %.3f %.3f  P(r>=0.8) %.3f'%(np.mean(rs),*np.percentile(rs,[16,84]),np.mean(np.array(rs)>=.8)))
a=load(True);a=a[a.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])]
adev=load(False);adev=adev[adev.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])]
sim=pd.read_parquet(R+'/sim_nss.parquet')
print('sim cols',list(sim.columns)[:40],len(sim))
def data_ratio(o,lo,hi):
    so=o[(o.nss_solution_type=='Orbital')&(o.period>=lo)&(o.period<hi)&(o.phot_g_mean_mag>=12)&(o.phot_g_mean_mag<16)]
    p,m=so[so.sense>0],so[so.sense<0];rr=[]
    for g in range(12,16):
        pg,mg=p[(p.phot_g_mean_mag>=g)&(p.phot_g_mean_mag<g+1)],m[(m.phot_g_mean_mag>=g)&(m.phot_g_mean_mag<g+1)]
        if min(len(pg),len(mg))>=10: rr.append((np.median(pg.parallax_error)/np.median(mg.parallax_error),len(pg)+len(mg)))
    return np.average([q[0] for q in rr],weights=[q[1] for q in rr]) if rr else np.nan
def model_frozen(lo,hi):
    b=sim[(sim.P>=lo)&(sim.P<hi)];x=b[(b.acc_plus|b.acc_minus)&(b.G>=12)&(b.G<16)]
    return np.nanmedian(x.s_plx_plus)/np.nanmedian(x.s_plx_minus)
def model_cond(lo,hi):
    b=sim[(sim.P>=lo)&(sim.P<hi)&(sim.G>=12)&(sim.G<16)]
    rr=[]
    for g in range(12,16):
        x=b[(b.G>=g)&(b.G<g+1)]
        p=x[x.acc_plus];m=x[x.acc_minus]
        if min(len(p),len(m))>=10: rr.append((np.nanmedian(p.s_plx_plus)/np.nanmedian(m.s_plx_minus),len(p)+len(m)))
    return np.average([q[0] for q in rr],weights=[q[1] for q in rr]) if rr else np.nan
def model_all(lo,hi):
    b=sim[(sim.P>=lo)&(sim.P<hi)&(sim.G>=12)&(sim.G<16)]
    return np.nanmedian(b.s_plx_plus)/np.nanmedian(b.s_plx_minus)
edges={'frozen':[50,100,150,200,250,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600,3000],
 'log12':list(np.round(np.geomspace(50,3000,13))),
 'log18':list(np.round(np.geomspace(50,3000,19))),
 'log24':list(np.round(np.geomspace(50,3000,25))),
 'lin100_100-1600':list(range(100,1700,100)),
 'lin50_100-1000':list(range(100,1050,50)),
 'frozen_shift+20':[e+20 for e in [50,100,150,200,250,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600]]+[3000],
 'frozen_no<100':[100,150,200,250,300,340,390,450,500,600,700,800,900,1000,1100,1300,1600,3000],
 'frozen_P<1000':[50,100,150,200,250,300,340,390,450,500,600,700,800,900,1000],
 'frozen_P<1038':[100,150,200,250,300,340,390,450,500,600,700,800,900,1000],
}
print('\nT1 by binning (heldout): r_frozen_def, med|d| ; r_conditional_sel; r_all_draws')
for k,e in edges.items():
    d=[];f=[];c=[];al=[]
    for lo,hi in zip(e[:-1],e[1:]):
        d.append(data_ratio(a,lo,hi));f.append(model_frozen(lo,hi));c.append(model_cond(lo,hi));al.append(model_all(lo,hi))
    d,f,c,al=map(np.array,(d,f,c,al));ok=np.isfinite(d)&np.isfinite(f)&np.isfinite(c)
    print('%-18s nb=%2d r=%.3f med=%.3f | cond r=%.3f med=%.3f | all r=%.3f med=%.3f'%(k,ok.sum(),np.corrcoef(d[ok],f[ok])[0,1],np.median(abs(d[ok]-f[ok])),np.corrcoef(d[ok],c[ok])[0,1],np.median(abs(d[ok]-c[ok])),np.corrcoef(d[ok],al[ok])[0,1],np.median(abs(d[ok]-al[ok]))))
e=edges['frozen']
print('\nP  data  model_frozen  model_cond  model_all')
for lo,hi in zip(e[:-1],e[1:]):
    print(lo,hi,'%.3f %.3f %.3f %.3f'%(data_ratio(a,lo,hi),model_frozen(lo,hi),model_cond(lo,hi),model_all(lo,hi)))
# null: replace model with trivial shapes
P=np.sqrt(np.array(e[:-1])*np.array(e[1:]))
dr=t.ratio.values
step=(P>300).astype(float)
print('\nnull model: step at P>300 d r=%.3f'%np.corrcoef(dr,step)[0,1])
# DR3 model s_plx scale vs data, by G
for g in [(12,13),(13,14),(14,15),(15,16),(16,17)]:
    for lo,hi in [(200,300),(600,900)]:
        x=sim[(sim.G>=g[0])&(sim.G<g[1])&(sim.P>=lo)&(sim.P<hi)&(sim.acc_minus)]
        y=a[(a.sense<0)&(a.phot_g_mean_mag>=g[0])&(a.phot_g_mean_mag<g[1])&(a.period>=lo)&(a.period<hi)&(a.nss_solution_type=='Orbital')]
        print('G',g,'P',lo,hi,'sigma_plx - model %.4f data %.4f ratio data/model %.2f'%(np.nanmedian(x.s_plx_minus),y.parallax_error.median(),y.parallax_error.median()/np.nanmedian(x.s_plx_minus)))
print('NaN frac s_plx',sim.s_plx_plus.isna().mean(),sim.s_plx_minus.isna().mean())
