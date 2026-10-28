"""Hunt H-0006, step 2: which faded-excess flags are stars, which survive the two traps, and why the last ones die.

  kind            star (Gaia parallax/error > 5, not a Gaia QSO/galaxy candidate), QSO/gal, faint/no plx, no Gaia
  robust_left     fraction of the 2014-15 excess (median W1-W2 of the first 4 visits) left in visits -5..-2, i.e.
                  ignoring the final visit: one bad last W2 point is enough to fake the sky-pass fade
  red_nbr         nearest CatWISE2020 source within 8" with W1-W2 > 0.8 (a dusty AGN blended into the WISE PSF)
  qso_nbr         Gaia DR3 source within 6" that Gaia calls a QSO/galaxy candidate or classifies as AGN
  drift_mas_yr    slope of the single-exposure NEOWISE RA offset from the star's own (proper-motion) track: a dust
                  excess on the star moves with it (0); a fixed background source drags the centroid
Writes hunts/H-0006/vetted.csv and plots/stars.png.
"""
import io
import time
from pathlib import Path

import httpx
import matplotlib
import numpy as np
import pandas as pd

from oddsky.data import neowise
from oddsky.data.gaia import adql

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

here = Path("hunts/H-0006")


def irsa(q: str, tries: int = 4) -> pd.DataFrame:
    for k in range(tries):
        r = httpx.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv", "LANG": "ADQL"},
                       timeout=300)
        if r.status_code < 500 or k == tries - 1:
            r.raise_for_status()
            return pd.read_csv(io.StringIO(r.text))
        time.sleep(15 * (k + 1))  # IRSA's TAP front end 504s under load


def robust_left(v: pd.DataFrame) -> float:
    c = (v.w1 - v.w2).to_numpy()
    if len(c) < 10:
        return np.nan
    return float(np.median(c[-5:-1]) / np.median(c[:4]))


def red_neighbour(r) -> str:
    cw = irsa(f"SELECT source_name, ra, dec, w1mpro, w2mpro, pmra FROM catwise_2020 WHERE "
              f"CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',{r.ra},{r.dec},{8 / 3600}))=1")
    cw["sep"] = np.hypot((cw.ra - r.ra) * np.cos(np.radians(r.dec)), cw.dec - r.dec) * 3600
    red = cw[(cw.w1mpro - cw.w2mpro > 0.8) & (cw.sep > 1.5)].sort_values("sep")
    return "" if red.empty else f"{red.source_name.iloc[0]} {red.sep.iloc[0]:.1f}\" W1-W2={red.w1mpro.iloc[0] - red.w2mpro.iloc[0]:.2f}"


def qso_neighbour(r) -> str:
    g = adql(f"SELECT g.source_id, g.phot_g_mean_mag AS gmag, g.in_qso_candidates AS q, g.in_galaxy_candidates AS gal, "
             f"c.best_class_name AS cls, DISTANCE(POINT({r.ra},{r.dec}),POINT(g.ra,g.dec))*3600 AS sep "
             f"FROM gaiadr3.gaia_source AS g LEFT OUTER JOIN gaiadr3.vari_classifier_result AS c ON c.source_id=g.source_id "
             f"WHERE 1=CONTAINS(POINT(g.ra,g.dec),CIRCLE({r.ra},{r.dec},{6 / 3600}))")
    bad = g[(g.q.astype(str) == "True") | (g.gal.astype(str) == "True") | (g.cls.astype(str) == "AGN")]
    return "" if bad.empty else f"Gaia DR3 {int(bad.source_id.iloc[0])} {bad.sep.iloc[0]:.1f}\" {bad.cls.iloc[0]}"


def drift(r) -> float:
    e, _ = neowise.fetch_exposures(r.ra, r.dec, 3.0)
    e = e[(e.qual_frame > 0) & (e.cc_flags == "0000")]
    yr = (e.mjd - 57388.0) / 365.25  # Gaia DR3 epoch 2016.0
    track = r.gaia_ra + r.gaia_pmra / 3.6e6 * yr / np.cos(np.radians(r.gaia_dec))
    dx = (e.ra - track) * np.cos(np.radians(r.dec)) * 3600
    return float(np.polyfit(yr, dx, 1)[0] * 1000)


def main() -> None:
    d = pd.read_csv(here / "flags.csv", dtype={"gaia_source_id": str})
    lc = pd.read_csv(here / "lightcurves.csv")
    d["kind"] = np.select([d.gaia_source_id.isna(), (d.gaia_qso_cand == True) | (d.gaia_gal_cand == True),  # noqa: E712
                           d.gaia_poe > 5], ["no Gaia", "QSO/gal", "star"], "faint/no plx")
    d["abs_g"] = d.gaia_g + 5 * np.log10(d.gaia_parallax.clip(lower=1e-3) / 100)
    d["robust_left"] = d.allwise_cntr.map(lambda c: robust_left(lc[lc.allwise_cntr == c]))
    print(d.kind.value_counts().to_string())
    s = d[d.kind == "star"].copy()
    s["final_visit_artifact"] = s.robust_left > 0.6
    live = s[~s.final_visit_artifact]
    print(len(s), "stars;", int(s.final_visit_artifact.sum()), "faded only in the final visit;", len(live), "left")
    # Gaia's own coordinates for the propagated track (the cone match kept only the photometry)
    ids = ",".join(live.gaia_source_id)
    pos = adql(f"SELECT source_id, ra, dec FROM gaiadr3.gaia_source WHERE source_id IN ({ids})")
    pos["source_id"] = pos.source_id.astype("int64").astype(str)
    live = live.merge(pos.rename(columns={"source_id": "gaia_source_id", "ra": "gaia_ra", "dec": "gaia_dec"}), on="gaia_source_id")
    live["red_nbr"] = [red_neighbour(r) for r in live.itertuples()]
    live["qso_nbr"] = [qso_neighbour(r) for r in live.itertuples()]
    live["drift_mas_yr"] = [drift(r) for r in live.itertuples()]
    out = s.merge(live[["allwise_cntr", "red_nbr", "qso_nbr", "drift_mas_yr"]], on="allwise_cntr", how="left")
    out["survives"] = (~out.final_visit_artifact & out.red_nbr.fillna("").eq("") & out.qso_nbr.fillna("").eq("")
                       & (out.drift_mas_yr.abs() < 10))
    cols = ["allwise_cntr", "designation", "ra", "dec", "gaia_source_id", "gaia_g", "gaia_bp_rp", "abs_g", "gaia_pmra",
            "gaia_mh", "color_base", "color_end", "robust_left", "final_visit_artifact", "red_nbr", "qso_nbr",
            "drift_mas_yr", "survives"]
    out[cols].to_csv(here / "vetted.csv", index=False)
    pd.set_option("display.width", 250)
    print(out[cols].round(2).to_string(index=False))

    (here / "plots").mkdir(exist_ok=True)
    n = len(out)
    fig, ax = plt.subplots((n + 3) // 4, 4, figsize=(16, 2.7 * ((n + 3) // 4)), squeeze=False)
    for a, r in zip(ax.flat, out.itertuples(), strict=False):
        v = lc[lc.allwise_cntr == r.allwise_cntr]
        a.plot(v.t, v.w1, "o", ms=3, c="#2836d9")
        a.plot(v.t, v.w2, "o", ms=3, c="#e0457b")
        a.invert_yaxis()
        why = "survives" if r.survives else ("final visit" if r.final_visit_artifact else "blend")
        a.set_title(f"{r.designation}  G={r.gaia_g:.1f} M_G={r.abs_g:.1f}\nexcess left {r.robust_left:.2f}: {why}", fontsize=7)
    for a in ax.flat[n:]:
        a.axis("off")
    plt.tight_layout()
    plt.savefig(here / "plots" / "stars.png", dpi=75)


if __name__ == "__main__":
    main()
