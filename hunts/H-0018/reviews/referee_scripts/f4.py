import numpy as np, pandas as pd, os, sys
from scipy import stats
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
import handedness as hd
from nss_rv_test import load
pd.set_option('display.width',220)
a=pd.concat([load(False),load(True)])
a=a[a.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])].copy()
def Af(s): 
    m=s.sense.mean(); return m,np.sqrt((1-m*m)/max(len(s),1)),len(s)
def fmt(s): return '%+.3f±%.3f(%d)'%Af(s) if len(s)>=20 else '  --  (%d)'%len(s)
def add_mref(z):
    z=z.copy()
    ref=z[z.sense<0].groupby(pd.cut(z[z.sense<0].phot_g_mean_mag,np.arange(5,20)),observed=True).parallax_error.median()
    z['m_ref']=z.parallax/pd.cut(z.phot_g_mean_mag,np.arange(5,20)).map(ref).astype(float)*z.period/20000
    return z
mb=[(0,1.5),(1.5,2.5),(2.5,5),(5,10),(10,1e9)]
print('=== T5 replicated by type and as control in other period zones (all data), A by sense-blind margin')
for lab,lo,hi in [('600-900',600,900),('340-390',340,390),('300-450',300,450),('150-200',150,200),('200-300',200,300),('500-600',500,600),('1100-3000',1100,3000),('50-100',50,100)]:
    z=add_mref(a[(a.period>=lo)&(a.period<hi)])
    o=z[z.nss_solution_type=='Orbital'];b=z[z.nss_solution_type=='AstroSpectroSB1']
    print(lab,'Orb:',' '.join(fmt(o[(o.m_ref>=l)&(o.m_ref<h)]) for l,h in mb));print('    SB1:',' '.join(fmt(b[(b.m_ref>=l)&(b.m_ref<h)]) for l,h in mb))
z=add_mref(a[(a.period>=600)&(a.period<900)])
z['m_a0']=z.significance*np.sqrt(z.period)/158
print('\n=== 600-900, A in margin x a0-significance margin (is the parallax cut distinct from the a0 cut?) rows m_ref, cols m_a0')
sb=[(0,1.5),(1.5,2.5),(2.5,5),(5,1e9)]
for l,h in mb:
    x=z[(z.m_ref>=l)&(z.m_ref<h)]
    print(l,h,' '.join(fmt(x[(x.m_a0>=sl)&(x.m_a0<sh)]) for sl,sh in sb))
print('\n=== 600-900, A in margin x G')
gb=[(5,12),(12,13),(13,14),(14,15),(15,16),(16,19)]
for l,h in mb:
    x=z[(z.m_ref>=l)&(z.m_ref<h)]
    print(l,h,' '.join(fmt(x[(x.phot_g_mean_mag>=g0)&(x.phot_g_mean_mag<g1)]) for g0,g1 in gb))
print('\n=== 600-900, A by parallax at fixed G (rows G)')
pb=[(0,1),(1,1.5),(1.5,2),(2,3),(3,5),(5,10),(10,1000)]
for g0,g1 in gb:
    x=z[(z.phot_g_mean_mag>=g0)&(z.phot_g_mean_mag<g1)]
    print(g0,g1,' '.join(fmt(x[(x.parallax>=p0)&(x.parallax<p1)]) for p0,p1 in pb))
print('\n=== raw margin (own sigma), 600-900, N+ and N-')
z['raw']=z.parallax/z.parallax_error*z.period/20000
for l,h in [(1,1.05),(1.05,1.1),(1.1,1.2),(1.2,1.5),(1.5,2),(2,3),(3,5),(5,1e9)]:
    x=z[(z.raw>=l)&(z.raw<h)&(z.nss_solution_type=='Orbital')]
    print('  raw[%.2f,%.3g) Orb %s'%(l,h,fmt(x)))
print('\n=== Spurious signatures, Orbital, P 600-900, by sense at matched G and m_ref bins (median + vs -), low margin and high margin')
o=z[z.nss_solution_type=='Orbital'].copy()
o['f_mf']=o.mf>0.3
cols=['mf','a0_au','eccentricity','significance','goodness_of_fit','efficiency','ruwe','ipd_frac_multi_peak','ipd_gof_harmonic_amplitude','astrometric_excess_noise','visibility_periods_used','bp_rp','phot_g_mean_mag','parallax','scan_direction_strength_k1','scan_direction_strength_k2','scan_direction_strength_k3','scan_direction_strength_k4','astrometric_matched_transits']
for lab,mask in [('m_ref<1.5',o.m_ref<1.5),('1.5<=m_ref<2.5',(o.m_ref>=1.5)&(o.m_ref<2.5)),('m_ref>=5',o.m_ref>=5)]:
    x=o[mask];p,m=x[x.sense>0],x[x.sense<0]
    print(lab,'N+',len(p),'N-',len(m),' frac mf>0.3: + %.4f  - %.4f'%(p.f_mf.mean(),m.f_mf.mean()))
    for c in cols:
        ks=stats.ks_2samp(p[c].dropna(),m[c].dropna())
        print('   %-30s med+ %9.4f med- %9.4f  KS D=%.3f p=%.2g'%(c,p[c].median(),m[c].median(),ks.statistic,ks.pvalue))
print('\n=== A by spurious proxy, Orbital 600-900 and m_ref<1.5 sub-bin')
for lab,col,bins in [('mf','mf',[0,.01,.03,.1,.2,.3,.5,1,100]),('ecc','eccentricity',[0,.1,.2,.3,.4,.5,.6,.7,.8,1]),('gof','goodness_of_fit',[-10,0,2,5,10,20,1000]),('eff','efficiency',[0,.3,.5,.7,.8,.9,1.01]),('ipdfmp','ipd_frac_multi_peak',[0,1,2,5,20,101]),('ipdgha','ipd_gof_harmonic_amplitude',[0,.02,.05,.1,.2,5]),('ruwe','ruwe',[1.4,2,3,5,10,100]),('vis','visibility_periods_used',[0,16,20,24,28,32,60]),('bprp','bp_rp',[-1,.5,.8,1,1.2,1.5,2,6])]:
    print(lab,'all :',' '.join('[%g,%g)%s'%(p0,p1,fmt(o[(o[col]>=p0)&(o[col]<p1)])) for p0,p1 in zip(bins[:-1],bins[1:])))
    q=o[o.m_ref<1.5];print(lab,'low :',' '.join('[%g,%g)%s'%(p0,p1,fmt(q[(q[col]>=p0)&(q[col]<p1)])) for p0,p1 in zip(bins[:-1],bins[1:])))
print('\n=== T3 reach: within RV sample (Orbital, 600-900, kpred>5, >=8 transits) vs full; A and RV rate by margin')
r=o[o.rv_chisq_pvalue.notna()&(o.rv_nb_transits>=8)&(o.kpred>5)]
print(' RV sample N',len(r),'A',fmt(r),'; share of Orbital 600-900 %.3f; G 5-95%%'%(len(r)/len(o)),np.percentile(r.phot_g_mean_mag,[5,50,95]),' full G',np.percentile(o.phot_g_mean_mag,[5,50,95]))
print(' Excess N- minus N+: full %d; in RV sample %d (%.1f%%)'%((o.sense<0).sum()-(o.sense>0).sum(),(r.sense<0).sum()-(r.sense>0).sum(),100*((r.sense<0).sum()-(r.sense>0).sum())/((o.sense<0).sum()-(o.sense>0).sum())))
allrv=o[o.rv_chisq_pvalue.notna()]
print(' any rv pvalue N',len(allrv),'G95',np.percentile(allrv.phot_g_mean_mag,95),'; share m_ref<1.5 in full %.3f, in RV sample %.3f'%((o.m_ref<1.5).mean(),(r.m_ref<1.5).mean()))
for l,h in mb:
    x=r[(r.m_ref>=l)&(r.m_ref<h)];p,m=x[x.sense>0],x[x.sense<0]
    if min(len(p),len(m))<5: print(' margin',l,h,'N',len(p),len(m));continue
    fp,fm=(p.rv_chisq_pvalue<.001).mean(),(m.rv_chisq_pvalue<.001).mean()
    print(' margin [%g,%.3g) N+ %d N- %d A %+.3f rate+ %.3f±%.3f rate- %.3f±%.3f'%(l,h,len(p),len(m),x.sense.mean(),fp,np.sqrt(fp*(1-fp)/len(p)),fm,np.sqrt(fm*(1-fm)/len(m))))
print(' relaxed: no kpred cut, any transits>=8, by margin')
r2=o[o.rv_chisq_pvalue.notna()&(o.rv_nb_transits>=8)]
for l,h in mb:
    x=r2[(r2.m_ref>=l)&(r2.m_ref<h)];p,m=x[x.sense>0],x[x.sense<0]
    if min(len(p),len(m))<5: continue
    fp,fm=(p.rv_chisq_pvalue<.001).mean(),(m.rv_chisq_pvalue<.001).mean()
    print(' margin [%g,%.3g) N+ %d N- %d A %+.3f rate+ %.3f rate- %.3f'%(l,h,len(p),len(m),x.sense.mean(),fp,fm))
print('\n=== RV amplitude vs K_pred: slope in log-log, by sense, and base rate of RV variable for low K')
for s,name in [(1,'+'),(-1,'-')]:
    x=r2[(r2.sense==s)&r2.rv_amplitude_robust.notna()&(r2.kpred>0)]
    lk,la=np.log10(x.kpred),np.log10(x.rv_amplitude_robust)
    q=np.isfinite(lk)&np.isfinite(la)
    print(name,'N',q.sum(),'spearman %.3f'%stats.spearmanr(lk[q],la[q]).statistic,'  rv_amp/2K by kpred bin:',[ (b0,round(float((x.rv_amplitude_robust/(2*x.kpred))[(x.kpred>=b0)&(x.kpred<b1)].median()),2),int(((x.kpred>=b0)&(x.kpred<b1)).sum())) for b0,b1 in [(0,1),(1,2),(2,5),(5,10),(10,20),(20,100)]],' RV var rate by k:',[round(float((x.rv_chisq_pvalue<.001)[(x.kpred>=b0)&(x.kpred<b1)].mean()),3) for b0,b1 in [(0,1),(1,2),(2,5),(5,10),(10,20),(20,100)]])
print('\n=== T3 assumption: how RV-variable is the rest of NSS? a fake orbit on a real binary: rate for Orbital kpred<1 (where the orbit predicts nothing):',round(float((r2[r2.kpred<1].rv_chisq_pvalue<.001).mean()),3),'N',int((r2.kpred<1).sum()))
print('\n=== SB1 as a test: RV-confirmed orbits at same P by margin, Excess N- minus N+ fraction: A:')
for lo,hi in [(300,450),(340,390),(600,900),(700,800),(50,100),(150,200)]:
    s=a[(a.period>=lo)&(a.period<hi)&(a.nss_solution_type=='AstroSpectroSB1')];print(' ',lo,hi,fmt(s),' %.1f sigma'%(s.sense.mean()/Af(s)[1]),' median G %.1f'%s.phot_g_mean_mag.median())
print('\n=== e dependence of ratio at 700-745 (README: 1.42,1.37,1.14,1.08 for e<0.2.. e>=0.6)')
q=a[(a.period>=700)&(a.period<745)&(a.nss_solution_type=='Orbital')&(a.phot_g_mean_mag>=12)&(a.phot_g_mean_mag<16)]
for e0,e1 in [(0,.2),(.2,.4),(.4,.6),(.6,1.0)]:
    x=q[(q.eccentricity>=e0)&(q.eccentricity<e1)];rr=[]
    for g in range(12,16):
        pg,mg=x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense>0)],x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense<0)]
        if min(len(pg),len(mg))>=10: rr.append((pg.parallax_error.median()/mg.parallax_error.median(),len(pg)+len(mg)))
    print(' e [%.1f,%.1f) ratio %.3f N=%d  A=%s'%(e0,e1,np.average([v[0] for v in rr],weights=[v[1] for v in rr]),len(x),fmt(x)))
print(' Same e split, control P where model says e not needed? 300-340 and 340-390, 600-700,800-900')
for lo,hi in [(340,390),(600,700),(800,900),(900,1000),(1100,1600)]:
    q=a[(a.period>=lo)&(a.period<hi)&(a.nss_solution_type=='Orbital')&(a.phot_g_mean_mag>=12)&(a.phot_g_mean_mag<16)];o2=[]
    for e0,e1 in [(0,.2),(.2,.4),(.4,.6),(.6,1.0)]:
        x=q[(q.eccentricity>=e0)&(q.eccentricity<e1)];rr=[]
        for g in range(12,16):
            pg,mg=x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense>0)],x[(x.phot_g_mean_mag>=g)&(x.phot_g_mean_mag<g+1)&(x.sense<0)]
            if min(len(pg),len(mg))>=10: rr.append((pg.parallax_error.median()/mg.parallax_error.median(),len(pg)+len(mg)))
        o2.append(round(float(np.average([v[0] for v in rr],weights=[v[1] for v in rr])),3) if rr else None)
    print(' ',lo,hi,o2)
