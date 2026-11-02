import sys, numpy as np
from astropy.table import Table
from astropy.time import Time
from astropy.coordinates import SkyCoord
t = Table.read(sys.argv[1], format='csv')
c = SkyCoord(156.2910,17.1639,unit='deg')
t['sep'] = SkyCoord(t['ra'],t['dec'],unit='deg').separation(c).arcsec
t['date'] = [Time(x,format='mjd').iso[:10] for x in t['obsTime']]
t['AB'] = [(-2.5*np.log10(f/3631.) if f>0 else np.nan) for f in t['psfFlux']]
filt = {1:'g',2:'r',3:'i',4:'z',5:'y'}; t['f'] = [filt[x] for x in t['filterID']]
print("MJD range", t['obsTime'].min(), t['obsTime'].max(), t['date'][0], t['date'][-1], "N=",len(t))
for o in sorted(set(t['objID'])):
    s = t[t['objID']==o]
    print(f"objID {o}: N={len(s)} sep={np.median(s['sep']):.2f}\" filters={''.join(s['f'])}  dates {s['date'][0]}..{s['date'][-1]}")
    for r in s: print(f"   {r['date']} MJD{r['obsTime']:.2f} {r['f']} {r['AB']:.2f} sep={r['sep']:.2f}\" qf={r['psfQfPerfect']:.2f}")
