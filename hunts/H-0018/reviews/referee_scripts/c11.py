import numpy as np, pandas as pd, sys, os
sys.path.insert(0,'/tmp/ref_h18/repl/scripts')
from nss_rv_test import load
import pyarrow.parquet as pq
print('cat rows',pq.ParquetFile(os.path.expanduser('~/oddsky-runs/h0018/data/elbadry/cat.parquet')).metadata.num_rows)
d=pd.concat([load(False),load(True)]);d=d[d.nss_solution_type.isin(['Orbital','AstroSpectroSB1'])]
print('e null',d.eccentricity.isna().sum(),'e==0',(d.eccentricity==0).sum(),'e<1e-3',(d.eccentricity<1e-3).sum(),'e<0.01',(d.eccentricity<.01).sum())
print(d.groupby('nss_solution_type').eccentricity.describe().round(3))
print('flags vc',d.flags.value_counts().head(8).to_dict())
o=d[d.nss_solution_type=='Orbital'];print('Orbital period vs e-null/0:')
x=o[o.eccentricity.isna()|(o.eccentricity==0)]
print(len(x),x.period.describe().round(1).to_dict())
print('duplicates core',d.source_id.duplicated().sum())
