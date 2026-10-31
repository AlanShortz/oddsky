"""r1b: J174401's optical ratio at the NEOWISE visit with a baseline taken at the same PSF width. The 01a baseline before 2020 was
observed with a 3.2-3.4 px PSF and reads ~100 uJy; from 2020 (PSF 2.5 px) it reads 366 uJy, like 02a-04a (355-415 uJy). Baseline:
o nights more than 400 d from the visit, 2020 onward, PSF major axis within 0.25 px of the event nights' median; event: o nights
within 15 d of the visit (01a and 02a). c likewise (03a/04a/02a baselines)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import DATA  # noqa: E402

nt = pd.read_csv(os.path.join(DATA, "r1_nightly_J174401.csv"))
for F in ("o", "c"):
    d = nt[nt.F == F]
    ev = d[np.abs(d.dvis) <= 15]
    pm = ev.maj.median()
    b = d[d.base & (d.t > 58850) & (np.abs(d.maj - pm) < 0.25)]
    w = 1 / ev.ujy_err**2
    fe = np.sum(w * ev.ujy) / np.sum(w)
    fe_err = max(1 / np.sqrt(np.sum(w)), np.std(ev.ujy, ddof=1) / np.sqrt(len(ev)))
    bm = np.median(b.ujy)
    be = 1.4826 * np.median(np.abs(b.ujy - bm)) / np.sqrt(len(b))
    print(f"{F}: {len(ev)} event nights (PSF median {pm:.2f}) mean {fe:.0f} +- {fe_err:.0f} uJy; baseline {len(b)} nights at matched PSF "
          f"(units {sorted(b.cam.unique())}) median {bm:.0f} +- {be:.0f} (scatter {1.4826 * np.median(np.abs(b.ujy - bm)):.0f}); "
          f"ratio {fe / bm:.2f} +- {np.hypot(fe_err / bm, fe * be / bm**2):.2f}")
