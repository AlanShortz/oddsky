import pandas as pd, numpy as np
pd.set_option('display.width',250)
d=pd.read_parquet('/tmp/h7ref/wide.parquet')
d=d[d.allwise_cntr.notna()&(d.r_allwise<1.5)&(d.nb==1)&(d.qual_frame>0)]
m=d.groupby(['allwise_cntr','lab']).agg(w1=('w1mpro','median'),w2=('w2mpro','median'),n=('mjd','size'),ra=('ra','median'),dec=('dec','median')).unstack('lab')
m=m.dropna(subset=[('w1','ev'),('w1','v15'),('w1','v17')])
ref1=(m['w1']['v15']+m['w1']['v17'])/2; ref2=(m['w2']['v15']+m['w2']['v17'])/2
m['dw1']=m['w1']['ev']-ref1; m['dw2']=m['w2']['ev']-ref2; m['w1ref']=ref1; m['nev']=m['n']['ev']
m['ctrl']=(m['w1']['v15']-m['w1']['v17']).abs()
ra0,dec0=60.1073758,32.5909576
m['sep']=3600*np.hypot((m['ra']['ev']-ra0)*np.cos(np.radians(dec0)),m['dec']['ev']-dec0)
s=m[['w1ref','dw1','dw2','ctrl','nev','sep']].copy(); s.columns=['w1ref','dw1','dw2','v15_v17','nev','sep']
print(len(s),'stars with W1<12.5 in all three visits within 20\'')
for lo,hi in [(6,10),(10,11),(11,12),(12,12.5)]:
    q=s[(s.w1ref>=lo)&(s.w1ref<hi)]; print(f'W1 {lo}-{hi}: n={len(q)} median dW1 {q.dw1.median():+.3f} (MAD {1.48*np.median(np.abs(q.dw1-q.dw1.median())):.3f}) dW2 {q.dw2.median():+.3f}')
print('|dW1|>0.3 (excluding target):'); print(s[(s.dw1.abs()>0.3)].sort_values('dw1').round(3).to_string())
print('|v15-v17|>0.3 count',(s.v15_v17>0.3).sum())
# frames in event visit
dd=pd.read_parquet('/tmp/h7ref/wide.parquet'); e=dd[dd.lab=='ev']
print('event frames:',e.groupby(['scan_id','frame_num']).size().shape[0])
print('sso_flg in wide event set:',e.sso_flg.sum())
print('brightest sources in 20\' during event:'); print(e.groupby('allwise_cntr').w1mpro.median().sort_values().head(5))
