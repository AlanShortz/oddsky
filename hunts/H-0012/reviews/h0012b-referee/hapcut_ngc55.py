from pathlib import Path
import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.mast import Hapcut
OUT = Path("~/oddsky-runs/imaging/scratch/h0012b-referee/hst_ngc55").expanduser(); OUT.mkdir(parents=True, exist_ok=True)
c = SkyCoord(3.80788, -39.2148, unit="deg")
m = Hapcut.download_cutouts(c, size=12 * u.arcsec, path=str(OUT))
for r in m: print(r)
