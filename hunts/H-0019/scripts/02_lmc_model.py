"""The counterfactual: what would two visits, a given time apart, see if a galaxy's bright red stars were the LMC's?

Population = every Gaia DR3 star in a central LMC box that moves with the LMC and is red and bright (the denominator), plus
OGLE-III long-period variables Gaia's cut missed. Variables carry OGLE's three periods and I amplitudes; the rest are
taken as constant. Output: work/lmc_population.csv and work/lmc_model.csv (variability against lag and magnitude above the
red-giant tip).
"""
import pathlib, json
import numpy as np, pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u

RUN = pathlib.Path.home() / "oddsky-runs/h0019"
WORK = pathlib.Path(__file__).resolve().parents[1] / "work"
import sys
CLOUD = sys.argv[1] if len(sys.argv) > 1 else "lmc"
# box, mean proper motion, observed (not dereddened) I of the tip (checked below against the luminosity function)
BOX, PM, I_TRGB_LMC = {"lmc": ((76.0, 84.0, -70.2, -69.2), (1.85, 0.30), 14.60),
                       "smc": ((9.0, 17.0, -73.5, -72.2), (0.75, -1.25), 15.00)}[CLOUD]
LAGS = [1, 3, 10, 30, 100, 200, 400, 1000, 3000]
rng = np.random.default_rng(19)


def load_ogle():
    rows = []
    for ln in (RUN / f"cat/ogle3_{CLOUD}_lpv.tsv").read_text().splitlines():
        if ln.startswith("#") or not ln[:5].strip().isdigit():
            continue
        p = [x.strip() for x in ln.split("\t")]
        rows.append(p)
    cols = ["star", "type", "evol", "spt", "ra_s", "dec_s", "I", "V", "P1", "A1", "P2", "A2", "P3", "A3"]
    if CLOUD == "smc":
        cols.remove("evol")
    df = pd.DataFrame(rows, columns=cols)
    for c in ["I", "V", "P1", "A1", "P2", "A2", "P3", "A3"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    c = SkyCoord(df.ra_s.values, df.dec_s.values, unit=(u.hourangle, u.deg))
    df["ra"], df["dec"] = c.ra.deg, c.dec.deg
    return df


def main():
    og = load_ogle()
    print("OGLE LPVs:", len(og), og.type.value_counts().to_dict())
    inbox = (og.ra > BOX[0]) & (og.ra < BOX[1]) & (og.dec > BOX[2]) & (og.dec < BOX[3])
    og = og[inbox].reset_index(drop=True)
    g = pd.read_csv(RUN / f"cat/gaia_{CLOUD}_box.csv")
    mem = (g.parallax.fillna(0) < 0.15 + 3 * g.parallax_error.fillna(0.1)) & (np.hypot(g.pmra - PM[0], g.pmdec - PM[1]) < 1.2)
    print("Gaia red bright:", len(g), "LMC members:", int(mem.sum()))
    g = g[mem].reset_index(drop=True)
    cg = SkyCoord(g.ra.values * u.deg, g.dec.values * u.deg)
    co = SkyCoord(og.ra.values * u.deg, og.dec.values * u.deg)
    idx, d2, _ = co.match_to_catalog_sky(cg)
    ok = d2.arcsec < 1.0
    print("OGLE in box:", len(og), "matched to Gaia members:", int(ok.sum()))
    # I from Gaia RP and colour, fitted on the matched low-amplitude stars
    m = og[ok].copy(); mg = g.iloc[idx[ok]].reset_index(drop=True)
    bprp = (mg.phot_bp_mean_mag - mg.phot_rp_mean_mag).values
    calm = (m.A1.values < 0.1) & np.isfinite(bprp) & np.isfinite(m.V.values)
    cI = np.polyfit(bprp[calm], (m.I.values - mg.phot_rp_mean_mag.values)[calm], 2)
    cVI = np.polyfit(bprp[calm], (m.V.values - m.I.values)[calm], 2)
    res = (m.I.values - mg.phot_rp_mean_mag.values)[calm] - np.polyval(cI, bprp[calm])
    print("I - RP fit:", np.round(cI, 4), "scatter", round(float(np.std(res)), 3))
    gb = (g.phot_bp_mean_mag - g.phot_rp_mean_mag).values
    pop = pd.DataFrame({"I": g.phot_rp_mean_mag.values + np.polyval(cI, gb), "VI": np.polyval(cVI, gb),
                        "P1": np.nan, "A1": 0.0, "P2": np.nan, "A2": 0.0, "P3": np.nan, "A3": 0.0, "type": "const", "spt": ""})
    for col in ["I", "P1", "A1", "P2", "A2", "P3", "A3", "type", "spt"]:
        pop.loc[idx[ok], col] = og.loc[ok, col].values
    vi = (og.V - og.I).values
    pop.loc[idx[ok], "VI"] = np.where(np.isfinite(vi[ok]), vi[ok], pop.loc[idx[ok], "VI"])
    extra = og[~ok].copy()
    extra["VI"] = (extra.V - extra.I).fillna(9.9)   # no V: too red for OGLE's V
    pop = pd.concat([pop, extra[["I", "VI", "P1", "A1", "P2", "A2", "P3", "A3", "type", "spt"]]], ignore_index=True)
    pop = pop[(pop.I < I_TRGB_LMC + 1.0) & (pop.VI > 1.2)].reset_index(drop=True)
    pop["rel"] = pop.I - I_TRGB_LMC
    # tip check: steepest rise of the luminosity function of all red members
    h, e = np.histogram(pop.I, bins=np.arange(I_TRGB_LMC - 0.8, I_TRGB_LMC + 0.8, 0.05))
    sob = np.convolve(h, [1, 1, 0, -1, -1], mode="same") / np.sqrt(np.convolve(h, [1, 1, 1, 1, 1], mode="same") + 1)
    print("LF edge (max Sobel) at I =", round(float(e[np.argmax(sob[2:-2]) + 2] + 0.025), 2))
    pop.to_csv(WORK / f"{CLOUD}_population.csv", index=False)
    out = []
    bins = [(-3.0, -2.0), (-2.0, -1.0), (-1.0, -0.5), (-0.5, 0.0), (0.0, 0.5), (0.5, 1.0)]
    for lo, hi in bins:
        s = pop[(pop.rel >= lo) & (pop.rel < hi)]
        n = len(s)
        row0 = dict(rel_lo=lo, rel_hi=hi, n=n, f_ogle=float((s.type != "const").mean()), f_mira=float((s.type == "Mira").mean()),
                    f_srv=float((s.type == "SRV").mean()), f_c=float((s.spt == "C").mean()))
        for lag in LAGS:
            d = np.zeros((40, n))
            for k in "123":
                P, A = s["P" + k].values, s["A" + k].fillna(0).values
                P = np.where(np.isfinite(P) & (P > 0), P, 1.0)
                ph = rng.uniform(0, 2 * np.pi, (40, n))
                d += A / 2 * (np.sin(ph + 2 * np.pi * lag / P) - np.sin(ph))
            a = np.abs(d).ravel()
            out.append({**row0, "lag": lag, "rms": float(np.sqrt(np.mean(d ** 2))), "f02": float((a > 0.2).mean()),
                        "f03": float((a > 0.3).mean()), "f05": float((a > 0.5).mean()), "f10": float((a > 1.0).mean())})
    m = pd.DataFrame(out); m.to_csv(WORK / f"{CLOUD}_model.csv", index=False)
    pd.set_option("display.width", 200)
    print(m[m.lag.isin([400, 3000])].round(3).to_string(index=False))


main()
