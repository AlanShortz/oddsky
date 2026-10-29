import pandas as pd, numpy as np
pd.set_option('display.width',250)
ex=pd.read_parquet('/tmp/h7ref/ex.parquet')
t=ex[ex.sep<3]
print(t[t.visit==14][['mjd','w1mpro','w2mpro','nb','na','w1rchi2','qual_frame','sep','scan_id','frame_num']].to_string())
print(ex[(ex.visit==14)&(ex.sep<15)][['mjd','w1mpro','w2mpro','nb','sep','scan_id']].sort_values('mjd').to_string())
ev=16
c=ex[(ex.sep>5)&ex.allwise_cntr.notna()&(ex.r_allwise<2)].copy()
c['dw1']=c.w1mpro-c.groupby('allwise_cntr').w1mpro.transform('median')
c['dw2']=c.w2mpro-c.groupby('allwise_cntr').w2mpro.transform('median')
cv=c[c.visit==ev].groupby('allwise_cntr').agg(n=('mjd','size'),w1=('w1mpro','median'),w2=('w2mpro','median'),dw1=('dw1','median'),dw2=('dw2','median'),sep=('sep','median'))
print(len(cv),'controls; median dW1 %.3f dW2 %.3f'%(cv.dw1.median(),cv.dw2.median()))
print(cv.sort_values('w1').round(3).to_string())
# all detections in the event visit: count per scan/frame, any unassociated detections
e=ex[ex.visit==ev]
print('event visit detections',len(e),' unassociated (no allwise within 2"):',(e.allwise_cntr.isna()|(e.r_allwise>2)).sum())
u=e[e.allwise_cntr.isna()|(e.r_allwise>2)]
print(u[['mjd','w1mpro','w2mpro','sep','ph_qual','sso_flg','cc_flags']].sort_values('mjd').to_string())
print('sso_flg anywhere in cone:',ex.sso_flg.value_counts().to_dict())
print('per-visit unassociated counts:',ex[ex.allwise_cntr.isna()|(ex.r_allwise>2)].groupby('visit').size().to_dict())
