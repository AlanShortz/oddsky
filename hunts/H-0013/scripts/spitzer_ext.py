"""H-0013 Spitzer extension: IRAC 2004-2019 difference light curves at the top candidates, and a joint
WISE + Spitzer recurrence fit over 20 years.

    uv run python hunts/H-0013/scripts/spitzer_ext.py --top 12 [--uids UID ...] [--pause 2]

For every target: an IRSA SIA query (spitzer_sha, IRAC1/IRAC2 post-BCD mosaics), then per galaxy each mosaic is
downloaded once, sampled at all targets in it and deleted (oddsky.imaging.spitzer.fetch_samples; the NGC 2403
mosaics already downloaded by the H-0012 referee are reused). Requests are sequential with a pause; failures are
recorded as errors in work/spitzer/errors.json, never as missing epochs.

Joint fit (oddsky.imaging.recurrence.fit_series): W1 and W2 (offsets per visit season) and IRAC [3.6] and [4.5]
(offsets per mission phase: cryogenic before 2009-05-15, warm after), each with its own amplitude, one outburst
train. Reported: period and its 1-sigma range, every cycle 2004-2024 with its own amplitude (detected / covered /
missing, and which instruments see it), and a within-group shuffle null.

Writes work/spitzer/<label>.json, work/spitzer_summary.csv, figures/spitzer_<label>.png.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h0013  # noqa: E402

from oddsky.imaging import metrics, spitzer  # noqa: E402
from oddsky.imaging import recurrence as rc  # noqa: E402

log = logging.getLogger("h0013.spitzer")
CRYO_END_MJD = 54966.0  # 2009-05-15
LOCAL = [Path("~/oddsky-runs/imaging/scratch/h0012b-referee/spitzer_ngc2403").expanduser(),
         Path("~/oddsky-runs/imaging/scratch/h0012b-referee/spitzer_ngc55").expanduser()]
SDIR = h0013.WORK / "spitzer"


def label_of(uid: str) -> str:
    return uid.replace("|", "_")


def wise_lc(uid: str) -> rc.LightCurve:
    m = h0013.load_merged()
    r = m[m.uid == uid].iloc[0]
    lcs = pd.read_parquet(h0013.RUN / r.tile / r.phot_galaxy / "lightcurves.parquet")
    return rc.from_long(lcs[lcs.group == r.group], metrics.align_seasons)


def joint_fit(L: rc.LightCurve, lcs: dict, n_null: int = 200) -> dict:
    ser = rc.series_from_lc(L)
    for b in ("I1", "I2"):
        d = lcs.get(b)
        if d is None or len(d["mjd"]) < 3:
            continue
        mjd = np.array(d["mjd"])
        ser.append(rc.Series(b, rc.mjd_to_year(mjd), np.array(d["dflux"]), np.array(d["err"]),
                             (mjd > CRYO_END_MJD).astype(int)).clean())
    bank = rc.series_bank(ser)
    f = rc.fit_series(ser, bank, return_all=True)
    scale = max(1.0, f["chi2_fit"] / f["dof"])
    cyc = rc.cycles_series(ser, *f["params"], f["amps"], scale)
    prof = rc.period_profile(f, scale)
    null = rc.shuffle_series_null(ser, n_null, seed=3, bank=bank)
    z_joint = rc.shape_test(ser, f["params"][0])["Z"]
    # WISE-only and Spitzer-only periods for comparison
    sp = [s for s in ser if s.name.startswith("I")]
    f_sp = rc.fit_series(sp) if sp and sum(s.t.size for s in sp) >= 8 else None
    return dict(P_yr=f["params"][0], P_lo=prof["P_lo"], P_hi=prof["P_hi"], t0=f["params"][1], tau_r=f["params"][2],
                tau_d=f["params"][3], F=f["F"], chi2r=f["chi2_fit"] / f["dof"], amps=f["amps"],
                p_shuffle=rc.p_value(null, f["F"]), n_null=n_null, Z_joint=z_joint,
                cycles=cyc, n_cycles_det=sum(c["detected"] for c in cyc), n_cycles_covered=sum(c["covered"] for c in cyc),
                n_cycles_missing=sum(c["missing"] for c in cyc),
                n_cycles_det_spitzer=sum(c["detected"] and any(i.startswith("I") for i in c["instruments"]) for c in cyc),
                P_spitzer_only=f_sp["params"][0] if f_sp else np.nan, F_spitzer_only=f_sp["F"] if f_sp else np.nan,
                n_spitzer={s.name: int(s.t.size) for s in sp},
                profile=dict(P=prof["P"].round(4).tolist(), best=prof["best"].round(2).tolist()),
                series=[dict(name=s.name, t=s.t.round(4).tolist(), y=s.y.round(2).tolist(), e=s.e.round(2).tolist(),
                             group=np.asarray(s.group).tolist()) for s in ser])


def figure(label: str, res: dict, lcs: dict, path: Path, title: str):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(13, 6.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[3.2, 1, 1, 1.2])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    tt = np.linspace(2004, 2025, 2000)
    h = rc.periodic_template(tt, res["P_yr"], res["t0"], res["tau_r"], res["tau_d"])
    for ax, names in ((ax0, ("W1", "I1")), (ax1, ("W2", "I2"))):
        for s in res["series"]:
            if s["name"] not in names:
                continue
            t, y, e, g = (np.array(s[k]) for k in ("t", "y", "e", "group"))
            A = res["amps"].get(s["name"], 0)
            # remove each group's offset relative to the model, for display
            y2 = y.copy()
            for gg in np.unique(g):
                m = g == gg
                hm = rc.periodic_template(t[m], res["P_yr"], res["t0"], res["tau_r"], res["tau_d"])
                w = 1 / e[m] ** 2
                y2[m] -= np.sum(w * (y[m] - A * hm)) / w.sum()
            scale = 1.0 if s["name"].startswith("I") else 0.171787 if s["name"] == "W2" else 0.30954
            col = "#1f5fa8" if s["name"].startswith("W") else "#d1495b"
            ax.errorbar(t, y2 * scale, e * scale, fmt="o" if s["name"].startswith("W") else "s", ms=3.5, lw=0.7, color=col,
                        label=f"{s['name']} ({'WISE' if s['name'].startswith('W') else 'IRAC'})")
            ax.plot(tt, A * h * scale, color=col, lw=0.8, alpha=0.5)
        for c in res["cycles"]:
            ax.axvline(c["t_peak"], color="0.6" if not c["detected"] else "k", lw=0.6, ls=":" if not c["detected"] else "-", alpha=0.6)
        ax.axhline(0, color="0.8", lw=0.5)
        ax.set_ylabel("change (uJy)")
        ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax1.set_xlabel("year")
    ax0.set_title(f"{title}: joint P = {res['P_yr']:.2f} yr [{res['P_lo']:.2f}-{res['P_hi']:.2f}], F = {res['F']:.0f}, "
                  f"p_shuffle = {res['p_shuffle']:.3f}, cycles detected {res['n_cycles_det']} "
                  f"(Spitzer {res['n_cycles_det_spitzer']}), missing {res['n_cycles_missing']}", fontsize=8)
    for k, b in enumerate(("I1", "I2")):
        d = lcs.get(b)
        if d is None:
            continue
        for j, (key, ttl) in enumerate((("reference", "median"), ("bright_minus_faint", "bright - faint"))):
            ax = fig.add_subplot(gs[k, 1 + j])
            im = d[key]
            if key == "reference":
                v0, v1 = np.nanpercentile(im, [5, 99.7])
                ax.imshow(np.arcsinh((im - v0) / max(v1 - v0, 1e-6) * 10), origin="lower", cmap="gray")
            else:
                v = np.nanpercentile(np.abs(im), 99.5)
                ax.imshow(im, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v)
            c = spitzer.N_GRID // 2
            ax.plot(c, c, "+", color="lime", ms=10)
            ax.plot(c + d["var_dx_px"], c + d["var_dy_px"], "x", color="orange", ms=8)
            ax.set_title(f"{b} {ttl} (36\")", fontsize=7)
            ax.set_xticks([])
            ax.set_yticks([])
    ax = fig.add_subplot(gs[:, 3])
    ax.plot(res["profile"]["P"], res["profile"]["best"], color="k", lw=0.8)
    ax.set_xscale("log")
    ax.set_xticks([2, 3, 5, 8, 12])
    ax.set_xticklabels(["2", "3", "5", "8", "12"])
    ax.minorticks_off()
    ax.set_xlabel("trial period (yr)")
    ax.set_ylabel("best dchi2")
    ax.axvline(res["P_yr"], color="#d1495b", lw=0.8)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--uids", nargs="*", default=[])
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--max-mosaics", type=int, default=200, help="per galaxy")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    SDIR.mkdir(parents=True, exist_ok=True)
    cands = pd.read_csv(h0013.WORK / "candidates_h0013.csv")
    sel = cands[cands.verdict.isin(["candidate", "flagged"])].head(a.top)
    uids = list(dict.fromkeys(list(sel.uid) + a.uids))
    allm = h0013.load_merged().set_index("uid")
    targets = allm.loc[uids, ["galaxy", "ra", "dec"]].reset_index()
    log.info("%d targets in %d galaxies", len(targets), targets.galaxy.nunique())
    errors_path = SDIR / "errors.json"
    errors = json.loads(errors_path.read_text()) if errors_path.exists() else []
    summary = []
    import httpx

    client = httpx.Client(headers={"User-Agent": spitzer.UA}, timeout=300, follow_redirects=True)
    for gal, g in targets.groupby("galaxy"):
        rows, qstat = {}, {}
        for _, t in g.iterrows():
            qcache = SDIR / f"sia_{label_of(t.uid)}.json"
            if qcache.exists():
                st, rr = json.loads(qcache.read_text())
            else:
                st, rr = spitzer.sia_query(t.ra, t.dec, client=client)
                time.sleep(a.pause)
                if st.startswith("ok"):
                    qcache.write_text(json.dumps([st, rr]))
            qstat[t.uid] = st
            if not st.startswith("ok"):
                errors.append(dict(uid=t.uid, stage="sia", error=st))
                log.warning("SIA %s: %s", t.uid, st)
            for r in rr:
                rows[r["url"]] = r
        rows = sorted(rows.values(), key=lambda r: r["t_min"])[: a.max_mosaics]
        log.info("%s: %d mosaics for %d targets", gal, len(rows), len(g))
        pos = {label_of(t.uid): (t.ra, t.dec) for _, t in g.iterrows()}
        samples, errs = spitzer.fetch_samples(rows, pos, h0013.OUT / "spitzer" / gal, pause=a.pause, local_dirs=LOCAL,
                                              client=client, log=log.info)
        errors += [dict(galaxy=gal, stage="mosaic", **e) for e in errs]
        errors_path.write_text(json.dumps(errors, indent=1))
        for _, t in g.iterrows():
            lab = label_of(t.uid)
            lcs = {b: spitzer.difference_lightcurve(samples[lab], b) for b in ("I1", "I2")}
            rec = dict(uid=t.uid, galaxy=gal, ra=t.ra, dec=t.dec, sia=qstat.get(t.uid),
                       n_I1=len(lcs["I1"]["mjd"]) if lcs["I1"] else 0, n_I2=len(lcs["I2"]["mjd"]) if lcs["I2"] else 0)
            for b in ("I1", "I2"):
                if lcs[b]:
                    rec[f"{b}_var_offset_arcsec"] = lcs[b]["var_offset_arcsec"]
                    rec[f"{b}_years"] = f"{rc.mjd_to_year(min(lcs[b]['mjd'])):.1f}-{rc.mjd_to_year(max(lcs[b]['mjd'])):.1f}"
            try:
                L = wise_lc(t.uid)
                res = joint_fit(L, lcs)
                rec.update({k: v for k, v in res.items() if not isinstance(v, (list, dict))})
                rec["peaks_det"] = json.dumps([round(c["t_peak"], 2) for c in res["cycles"] if c["detected"]])
                rec["peaks_missing"] = json.dumps([round(c["t_peak"], 2) for c in res["cycles"] if c["missing"]])
                (SDIR / f"{lab}.json").write_text(json.dumps(dict(target=rec, joint=res, spitzer=json.loads(spitzer.to_json(lcs))),
                                                             indent=1, default=float))
                figure(lab, res, lcs, h0013.HERE / "figures" / f"spitzer_{lab}.png", f"{gal} {t.uid.split('|')[-1]}")
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"[:200]
                log.warning("joint fit %s: %s", t.uid, rec["error"])
            summary.append(rec)
            log.info("%s: I1 %d I2 %d epochs; joint P %.2f F %.0f cycles %s missing %s", t.uid, rec["n_I1"], rec["n_I2"],
                     rec.get("P_yr", np.nan), rec.get("F", np.nan), rec.get("peaks_det"), rec.get("peaks_missing"))
    new = pd.DataFrame(summary)
    sp = h0013.WORK / "spitzer_summary.csv"
    if sp.exists():  # keep earlier targets, replace the ones rerun now
        old = pd.read_csv(sp)
        new = pd.concat([old[~old.uid.isin(new.uid)], new], ignore_index=True)
    new.to_csv(sp, index=False)


if __name__ == "__main__":
    main()
