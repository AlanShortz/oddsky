import numpy as np, pandas as pd, os, re
from astropy import units as u
from astropy.coordinates import SkyCoord
R=os.path.expanduser('~/oddsky-runs/h0018')
lines=open('/tmp/ref_h18/orb6/orb6orbits.txt',errors='replace').read().split('\n')
hdr=[i for i,l in enumerate(lines) if l.startswith('RA,Dec')][0]
h=lines[hdr]
pP=h.index('PPPP'); pI=h.index('III.IIII'); pN=h.index('NNN.NNNN'); pA=h.index('AAA.AAAAA')
print(h[pP:pP+13],h[pI:pI+8]);
rows=[]
for l in lines[hdr+1:]:
    if len(l)<pI+8: continue
    m=re.match(r'(\d{2})(\d{2})(\d{2}\.\d+)([+-])(\d{2})(\d{2})(\d{2}\.?\d*)',l[:18])
    if not m: continue
    try:
        ra=15*(int(m[1])+int(m[2])/60+float(m[3])/3600); dec=(1 if m[4]=='+' else -1)*(int(m[5])+int(m[6])/60+float(m[7])/3600)
        ps=l[pP:pP+13]; 
        pv=float(re.findall(r'[\d.]+',ps)[0]); unit=re.findall(r'[a-zA-Z]',ps)
        unit=unit[0] if unit else 'y'
        Pd=pv*{'y':365.25,'d':1,'h':1/24,'m':1/1440,'c':36525,'k':365250}[unit]
        inc=float(l[pI:pI+8])
        grade=l[233:] 
    except Exception: continue
    rows.append((ra,dec,Pd,inc,l[19:29],l.rstrip()[-3:]))
o=pd.DataFrame(rows,columns=['ra','dec','P','inc','wds','tail'])
print('orb6 parsed',len(o),'P<5000d',(o.P<5000).sum(),'i>90 frac',(o.inc>90).mean())
d=pd.read_csv(R+'/data/nss/nss_astrometric.csv',dtype={'source_id':'int64'})
d['y']=np.sign(d.b_thiele_innes*d.f_thiele_innes-d.a_thiele_innes*d.g_thiele_innes)
c1=SkyCoord(o.ra.values*u.deg,o.dec.values*u.deg);c2=SkyCoord(d.ra.values*u.deg,d.dec.values*u.deg)
idx,sep,_=c1.match_to_catalog_sky(c2)
o['sep']=sep.arcsec;o['j']=idx
m=o[o.sep<15].copy()
for c in ['y','period','source_id','nss_solution_type','phot_g_mean_mag','parallax','significance','eccentricity']:
    m[c]=d[c].values[m.j.values]
m['pr']=m.period/m.P
m['pred']=np.where(m.inc>90,1,-1)  # i>90 retrograde on sky = clockwise = L.n>0
m=m[np.abs(m.inc-90)>0.0]
print('matches <15"',len(m))
pd.set_option('display.width',200);pd.set_option('display.max_rows',200)
g=m[(m.pr>0.7)&(m.pr<1.4)].sort_values('period')
print(g[['wds','P','period','inc','y','pred','sep','phot_g_mean_mag','nss_solution_type']].round(2).to_string())
print('period-matched N',len(g),'agree',(g.y==g.pred).sum())
g2=g[np.abs(g.inc-90)>10]
print('|i-90|>10 N',len(g2),'agree',(g2.y==g2.pred).sum())
