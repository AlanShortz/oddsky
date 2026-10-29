import pandas as pd, numpy as np, io
from astropy.io import ascii as aascii
from oddsky.data.http import request
G="https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"
cols="ra,dec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,qual_frame,nb,na,w1rchi2,w2rchi2,allwise_cntr,r_allwise,scan_id,frame_num,cc_flags,ph_qual,sso_flg"
out=[]
for lo,hi,lab in [(57992.4,57993.7,'ev'),(57794.0,57795.0,'v15'),(58151.0,58152.2,'v17')]:
    p=dict(catalog="neowiser_p1bs_psd",spatial="cone",radius=1200,radunits="arcsec",objstr="60.1073758 32.5909576",outfmt=1,selcols=cols,
           constraints=f"mjd between {lo} and {hi} and w1mpro < 12.5")
    r=request("GET",G,params=p,timeout=900)
    d=aascii.read(r.text.splitlines(),format="ipac").to_pandas(); d['lab']=lab; out.append(d); print(lab,len(d),d.mjd.min(),d.mjd.max())
pd.concat(out).to_parquet('/tmp/h7ref/wide.parquet')
