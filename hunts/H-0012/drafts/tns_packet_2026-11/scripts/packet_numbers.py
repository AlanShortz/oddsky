"""TNS packet 2026-11: compile the report numbers of the ready candidates into one JSON (numbers.json in the packet).

Inputs (scratch, outside the repo): lc/lc_all.csv (lc_screen.py), numbers_m81/loo_lightcurve.csv (recompute_m81.py),
timing/timing_*.csv (timing_at_source.py), astrometry/astrometry.json, spitzer/spitzer_ngc4945.json.

Photometry rules (as for OS-0030):
- flux vs a pre-event, leave-one-out, per-season reference; AB = -2.5 log10(f / 3631 Jy) from the unWISE Vega zero
  points (F0 = 309.540 / 171.787 Jy); Vega given alongside;
- the error is the larger of the propagated and the empirical (offset-aperture) error; for M81 the full-stack
  recompute is the primary flux and the larger of its error and the cutout empirical error is quoted;
- discovery = first epoch with >= 5 sigma in either band after the pre-event window; last non-detection = the epoch
  before it; limits are 5 sigma (3 sigma also given);
- times are the mean of the NEOWISE-R L1b exposures (qual_frame > 0) covering the source in that epoch.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/packet_numbers.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u

S = Path.home() / "oddsky-runs/imaging/scratch/tns-packet-2026-11"
PK = Path(__file__).resolve().parents[1]
F0 = {1: 309.540, 2: 171.787}


def ab(f):
    return float(-2.5 * np.log10(f * 1e-6 / 3631))


def vega(f, b):
    return float(-2.5 * np.log10(f * 1e-6 / F0[b]))


def phot(f, e, b):
    d = dict(uJy=round(float(f), 1), e_uJy=round(float(e), 1), snr=round(float(f / e), 1),
             lim5_AB=round(ab(5 * e), 2), lim3_AB=round(ab(3 * e), 2))
    if f > 0:
        d.update(AB=round(ab(f), 2), e_AB=round(1.0857 * e / f, 2), Vega=round(vega(f, b), 2))
    return d


ast = json.loads((S / "astrometry/astrometry.json").read_text())
lc = pd.read_csv(S / "lc/lc_all.csv")
out = {}
for lab, rank, tl in (("NGC4945_obs3", 3, "timing_NGC4945_obs3.csv"), ("M81_OS-0035", 8, "timing_M81_OS-0035.csv")):
    t = pd.read_csv(S / "timing" / tl)
    L = lc[lc["rank"] == rank].copy()
    if lab == "M81_OS-0035":  # full-stack recompute as primary flux; quote the larger error
        fs = pd.read_csv(S / "numbers_m81/loo_lightcurve.csv")
        L = L.merge(fs[["band", "epoch", "uJy", "e_uJy"]].rename(columns={"uJy": "f_full", "e_uJy": "e_full"}),
                    on=["band", "epoch"], how="left")
        L["flux"] = L.f_full
        L["err"] = np.fmax(L.e_full, L.e_emp.fillna(0))
        pre_lo = 2014.6
    else:
        L["flux"] = L.uJy
        L["err"] = L.e_uJy
        pre_lo = 2009.0
    pre_hi = {3: 2018.0, 8: 2023.5}[rank]
    L["snr"] = L.flux / L.err
    post = L[(L.year >= pre_hi) & np.isfinite(L.snr)]
    det = post[post.snr >= 5]
    disc_ep = int(det.epoch.min())
    epochs = sorted(L.epoch.unique())
    lnd_ep = max(e for e in epochs if e < disc_ep and np.isfinite(L[(L.epoch == e)].flux).all())

    def tim(ep):
        r = t[(t.epoch == ep) & (t.band == 1)].iloc[0]
        rec = dict(epoch=int(ep), mjd_mean=round(float(r.mjd_mean_qual), 3),
                   utc_mean=Time(float(r.mjd_mean_qual), format="mjd").iso[:19],
                   utc_first=str(r.utc_first)[:16], utc_last=str(r.utc_last)[:16],
                   n_frames_qual=int(r.n_frames_qual_gt0), exptime_s=round(7.7 * int(r.n_frames_qual_gt0), 1))
        if "n_m_at_source" in r and np.isfinite(r.n_m_at_source):
            rec["n_m_at_source_W1"] = int(r.n_m_at_source)
        if "tile_mjdmin" in r and np.isfinite(r.tile_mjdmin):
            rec["tile_mid_mjd"] = round(0.5 * (r.tile_mjdmin + r.tile_mjdmax), 3)
        else:
            rec["tile_mid_mjd"] = round(float(r.tile_mid_mjd), 3)
        return rec

    def ep_phot(ep):
        return {f"W{b}": phot(float(L[(L.epoch == ep) & (L.band == b)].flux.iloc[0]),
                             float(L[(L.epoch == ep) & (L.band == b)].err.iloc[0]), b) for b in (1, 2)}

    pk_ep = int(L[(L.band == 1) & np.isfinite(L.flux)].sort_values("flux").epoch.iloc[-1])
    later = [e for e in epochs if e > disc_ep and np.isfinite(L[L.epoch == e].flux).all()]
    pre = L[(L.year >= pre_lo) & (L.year < pre_hi)]
    a = ast[lab]
    c = SkyCoord(*a["position_gaia_tied"], unit="deg")
    out[lab] = dict(
        position=dict(ra_deg=round(a["position_gaia_tied"][0], 6), dec_deg=round(a["position_gaia_tied"][1], 6),
                      ra_hms=c.ra.to_string(u.hour, sep=":", precision=3, pad=True),
                      dec_dms=c.dec.to_string(u.deg, sep=":", precision=2, alwayssign=True, pad=True),
                      err_arcsec_quoted=0.5, err_arcsec_formal=[round(x, 2) for x in a["err_arcsec"]],
                      wise_minus_gaia_tile_offset=[round(x, 2) for x in a["wise_minus_gaia_arcsec"]],
                      centroid_tile_wcs=a["centroid_tile_wcs"]),
        discovery=dict(time=tim(disc_ep), phot=ep_phot(disc_ep)),
        last_nondetection=dict(time=tim(lnd_ep), phot=ep_phot(lnd_ep)),
        peak_W1=dict(time=tim(pk_ep), phot=ep_phot(pk_ep)),
        later=[dict(time=tim(e), phot=ep_phot(e)) for e in later if e != pk_ep],
        pre_event_rms_uJy={f"W{b}": round(float(pre[pre.band == b].flux.std()), 1) for b in (1, 2)},
        pre_event_max_abs_snr={f"W{b}": round(float(pre[pre.band == b].snr.abs().max()), 1) for b in (1, 2)},
        first_ge5sigma_epoch_by_band={f"W{b}": int(post[(post.band == b) & (post.snr >= 5)].epoch.min()) for b in (1, 2)},
        light_curve=L[["band", "epoch", "year", "flux", "err", "snr"]].round(3).to_dict("records"),
    )
    if lab == "M81_OS-0035":
        early = L[(L.year < 2011)]
        out[lab]["epoch2010_vs_2014_2023"] = [dict(band=int(r.band), year=round(r.year, 3), uJy=round(r.flux, 1),
                                                   e=round(r.err, 1)) for r in early.itertuples()]
    if lab == "NGC4945_obs3":
        # Spitzer/IRAC (spitzer_ngc4945.py): the centroid of the brightening (2019 - 2013-2017) in [3.6] and [4.5]
        # agree to 0.13" and lie 0.19" from the pre-existing SEIP 4.5 um source, so the Spitzer position is reported
        # (as the HST position was for OS-0030); the Gaia-tied WISE centroid is kept as the alternative.
        sp = json.loads((S / "spitzer/spitzer_ngc4945.json").read_text())
        ra = 0.5 * (sp["I1"]["centroid"]["ra"] + sp["I2"]["centroid"]["ra"])
        de = 0.5 * (sp["I1"]["centroid"]["dec"] + sp["I2"]["centroid"]["dec"])
        cs = SkyCoord(ra, de, unit="deg")
        out[lab]["wise_position"] = out[lab]["position"]
        out[lab]["position"] = dict(
            ra_deg=round(ra, 6), dec_deg=round(de, 6), ra_hms=cs.ra.to_string(u.hour, sep=":", precision=3, pad=True),
            dec_dms=cs.dec.to_string(u.deg, sep=":", precision=2, alwayssign=True, pad=True), err_arcsec_quoted=0.3,
            source="Spitzer/IRAC centroid of the 2019 brightening, mean of [3.6] and [4.5]",
            sep_I1_I2_arcsec=round(SkyCoord(sp["I1"]["centroid"]["ra"], sp["I1"]["centroid"]["dec"], unit="deg").separation(
                SkyCoord(sp["I2"]["centroid"]["ra"], sp["I2"]["centroid"]["dec"], unit="deg")).arcsec, 2),
            sep_from_wise_arcsec=round(cs.separation(SkyCoord(c.ra, c.dec)).arcsec, 2),
            sep_from_seip_progenitor_arcsec=round(cs.separation(SkyCoord(196.469643, -49.416208, unit="deg")).arcsec, 2))
        # Coordinator decision 2026-11-03: the TNS discovery is the earliest >= 5 sigma detection, Spitzer [3.6]
        # on 2018-06-02 (spitzer_discovery.py: LOO reference = 12 flat 2013-2016 epochs, exposure mid-time of the
        # BCD frames containing the source). The WISE first detection / last non-detection are kept as wise_*.
        dsc = json.loads((S / "spitzer/discovery.json").read_text())
        out[lab]["wise_first_detection"] = out[lab].pop("discovery")
        out[lab]["wise_last_nondetection"] = out[lab].pop("last_nondetection")

        def sp_ep(band, aor):
            x = [r for r in dsc["lc"][band] if r["aor"] == aor][0]
            t = dsc["timing_at_source"][f"{aor}_{band}"]
            return dict(band={"I1": "[3.6]", "I2": "[4.5]"}[band], aor=aor, proposal=t["proposal"], pi=t["pi"],
                        utc_mid=t["utc_mid"], mjd_mid=round(t["mjd_mid"], 4), utc_first=t["utc_first"],
                        utc_last=t["utc_last"], n_frames=t["n_frames"], exptime_s=t["exptime_s"],
                        **{k: x[k] for k in ("uJy", "e_uJy", "snr", "lim5_AB", "lim3_AB", "AB", "e_AB") if k in x})

        out[lab]["discovery"] = dict(instrument="SST - IRAC", phot=[sp_ep("I1", "60808960")],
                                     note="[4.5] did not cover the position in AOR 60808960 (no BCD frame at the source)")
        out[lab]["last_nondetection"] = dict(instrument="SST - IRAC", phot=[sp_ep("I1", "60808704"), sp_ep("I2", "60808704")])
        out[lab]["spitzer_lc"] = dsc["lc"]
        out[lab]["spitzer_ref_rms_uJy"] = {b: round(float(np.std([r["uJy"] for r in dsc["lc"][b] if r["in_ref"]])), 1)
                                           for b in ("I1", "I2")}
    print(lab, json.dumps({k: v for k, v in out[lab].items() if k != "light_curve"}, indent=1))
(PK / "numbers.json").write_text(json.dumps(out, indent=1))
