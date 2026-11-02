"""H-0012 v2 (referee triage report, 2026-11-01): galaxy-core masks, fine noise, forced photometry at known
positions, runner galaxies and centres, the v2 failed-SN score, the cutout dipole test and the injection-
recovery machinery. Synthetic data only; no network."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from astropy.wcs import WCS

from oddsky.imaging import detect, masks, psf
from oddsky.imaging.galaxies import GALAXIES, Galaxy, by_ungc_name
from oddsky.imaging.pipeline import (
    Config,
    analyse_stack,
    candidates_from,
    forced_known,
    recall_summary,
)
from oddsky.imaging.stack import EpochStack

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mt = sys.modules.get("merge_triage") or _load("merge_triage", ROOT / "hunts/H-0012/scripts/merge_triage.py")
it = _load("imaging_tile_v2", ROOT / "infra/gcp/imaging_tile.py")
tg = _load("targets_v2", ROOT / "hunts/H-0012/scripts/targets.py")

N = 120
MJD = 55210 + 182.6 * np.r_[0, 1, 2, np.arange(8, 27)]
SIGMA = 1.0


def _wcs(n=N):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [10.0, 40.0]
    w.wcs.crpix = [n / 2 + 0.5, n / 2 + 0.5]
    w.wcs.cdelt = [-2.75 / 3600, 2.75 / 3600]
    return w


def _gpsf(fwhm=2.3):
    return psf.gaussian_psf(fwhm)


def _add(img, p, x, y, f):
    h = p.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    img[yi - h:yi + h + 1, xi - h:xi + h + 1] += f * psf.shifted(p, x - xi, y - yi)


def _disc(shape, x, y, r):
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    return (xx - x) ** 2 + (yy - y) ** 2 <= r * r


CORE = (60.0, 60.0)
STAR = (100.0, 25.0)
SN = (76.0, 60.0)  # 44" from the core: outside a 10" nucleus circle, inside the core's "star" footprint


def _bitmask():
    m = np.zeros((N, N), np.int64)
    core_fp = _disc(m.shape, *CORE, 26)
    m[core_fp] |= (1 << 0) | (1 << 2)
    m[_disc(m.shape, CORE[0], CORE[1] + 20, 6)] |= 1 << 27  # a 'spike' of the core
    m[int(CORE[1]) - 1:int(CORE[1]) + 2, int(CORE[0]) - 1:int(CORE[0]) + 2] |= 1 << 21
    m[int(CORE[1]), int(CORE[0])] |= 1 << 4  # saturation
    m[_disc(m.shape, *STAR, 10)] |= (1 << 0) | (1 << 2)
    m[int(STAR[1]) - 1:int(STAR[1]) + 2, int(STAR[0]) - 1:int(STAR[0]) + 2] |= 1 << 21
    m[int(STAR[1]), int(STAR[0])] |= 1 << 4  # the real star's saturation zone
    m[_disc(m.shape, 30, 95, 4)] |= 1 << 13  # a latent: never released
    return m


def _galaxy(cat=True, nucleus=10.0):
    w = _wcs()
    (cra, cdec), (sra, sdec) = w.all_pix2world([CORE, STAR], 0)
    bs = ((float(cra), float(cdec), 6.0, False), (float(sra), float(sdec), 8.0, True)) if cat else ()
    return Galaxy("SYN", float(cra), float(cdec), 30.0, 1.0, 0.0, 5.0, nucleus_mask_arcsec=nucleus, search_scale=1.0,
                  bright_sources=bs)


# ---------------------------------------------------------------------------------------------- masks


def test_release_map_frees_galaxy_core_and_keeps_real_star():
    m = _bitmask()
    gal = _galaxy()
    cen = masks.classify_centres(m, _wcs(), gal)
    own = [c for c in cen if c.own]
    assert len(own) == 1 and abs(own[0].x - CORE[0]) < 1
    rel = masks.release_map(m, cen)
    assert rel[int(SN[1]), int(SN[0])]  # the core footprint is searched
    assert rel[int(CORE[1]) + 20, int(CORE[0])]  # and its spike
    assert not rel[int(STAR[1]), int(STAR[0]) + 5]  # the Gaia star's footprint stays masked
    assert rel[int(CORE[1]), int(CORE[0])]  # the core's MODEL saturation bit goes with its footprint
    assert not rel[95, 30]  # a latent is not a footprint bit


def test_fallback_rule_uses_core_position_and_extent():
    m = _bitmask()
    gal = _galaxy(cat=False)
    yy, xx = np.mgrid[:N, :N]
    ref = 2000 * np.exp(-0.5 * ((xx - CORE[0]) ** 2 + (yy - CORE[1]) ** 2) / 5.0**2)
    cen = masks.classify_centres(m, _wcs(), gal, ref=ref, psf=_gpsf())
    core = min(cen, key=lambda c: np.hypot(c.x - CORE[0], c.y - CORE[1]))
    star = min(cen, key=lambda c: np.hypot(c.x - STAR[0], c.y - STAR[1]))
    assert core.own and "extended" in core.why
    assert not star.own  # far from any galaxy core
    # a point-like source at the core position (a foreground star on the nucleus) is kept
    ref_pt = np.zeros((N, N))
    _add(ref_pt, _gpsf(), CORE[0], CORE[1], 5e4)
    cen = masks.classify_centres(m, _wcs(), gal, ref=ref_pt, psf=_gpsf())
    assert not min(cen, key=lambda c: np.hypot(c.x - CORE[0], c.y - CORE[1])).own


def test_concentration_separates_point_and_extended():
    p = _gpsf()
    assert masks.psf_concentration(p) > 0.7
    yy, xx = np.mgrid[:40, :40]
    ext = np.exp(-0.5 * ((xx - 20) ** 2 + (yy - 20) ** 2) / 4.0**2)
    assert masks.concentration(ext, 20, 20) < 0.5 * masks.psf_concentration(p)


@pytest.fixture(scope="module")
def core_run():
    """A galaxy whose bright extended core sits in an unWISE 'bright star' footprint, a transient 44" from
    the core inside that footprint, and a genuine foreground star with its own footprint."""
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:N, 0:N]
    core = 3000.0 * np.exp(-0.5 * ((xx - CORE[0]) ** 2 + (yy - CORE[1]) ** 2) / 6.0**2) + \
        60.0 * np.exp(-np.hypot(xx - CORE[0], yy - CORE[1]) / 25.0)
    p = _gpsf()
    stars = [(rng.uniform(12, N - 12), rng.uniform(12, N - 12), rng.uniform(150, 1500)) for _ in range(25)]
    stars += [(STAR[0], STAR[1], 5000.0), (20.3, 99.6, 4000.0), (95.4, 95.7, 3000.0), (15.5, 15.5, 3500.0)]
    img = np.empty((MJD.size, N, N), np.float32)
    for i in range(MJD.size):
        im = core.copy()
        for x, y, f in stars:
            _add(im, p, x, y, f)
        if 12 <= i <= 14:  # a transient in three epochs (both seasons)
            _add(im, p, *SN, 400.0)
        img[i] = im + rng.normal(0, SIGMA, im.shape)
    out = {}
    for release in (True, False):
        st = EpochStack(tile="", band=1, epochs=np.arange(MJD.size), mjd=MJD.copy(), img=img.copy(),
                        ivar=np.full_like(img, 1 / SIGMA**2), wcs=_wcs(), window=(0, N, 0, N))
        st.bitmask = _bitmask()
        cfg = Config(box=40, block=N, release_galaxy_cores=release)
        dets, prod = analyse_stack(st, _galaxy(), cfg)
        out[release] = (dets, prod, cfg)
    return out


def _near(d, x, y, r=2.0):
    return np.hypot(d.x - x, d.y - y) < r


def test_transient_in_core_footprint_found_only_with_v2_and_flagged(core_run):
    d2, prod2, cfg2 = core_run[True]
    d1, _, cfg1 = core_run[False]
    hit2 = d2[_near(d2, *SN)]
    assert len(hit2) >= 2 and hit2.low_confidence.all()
    assert not _near(d1, *SN).any()  # v1 masks the whole footprint
    c = candidates_from(d2, cfg2)
    assert c.low_confidence.any()
    ms = prod2["masks"]
    assert ms.bright[int(STAR[1]), int(STAR[0]) + 5]  # real star still masked
    assert not ms.saturated[int(CORE[1]), int(CORE[0])]  # model saturation of galaxy light: not saturated...
    assert ms.lowconf[int(SN[1]), int(SN[0])]


def test_mask_census_reports_before_after(core_run):
    cen = core_run[True][1]["mask_census"]
    assert cen["masked_v2"] < cen["masked_v1"]
    assert cen["released_lowconf"] > 0.05
    assert cen["light_masked_v2"] < cen["light_masked_v1"]
    assert cen["n_released_sources"] == 1


def test_fine_noise_never_below_coarse_and_rises_on_structure():
    rng = np.random.default_rng(0)
    snr = rng.normal(0, 1, (128, 128)).astype(np.float32)
    snr[40:72, 40:72] *= 3.0  # structured residuals in a 32-px patch
    fine = np.zeros_like(snr, bool)
    fine[32:80, 32:80] = True
    c = detect.local_scatter(snr, None, box=64)
    cf = detect.fine_scatter(snr, None, fine, box=16)
    comb = np.where(fine & np.isfinite(cf), np.fmax(c, cf), c)
    assert (comb >= c - 1e-6).all()
    assert comb[56, 56] > 2.0 and comb[56, 56] > 1.3 * c[56, 56]
    assert np.isnan(cf[120, 120])  # only computed near the fine zone (bbox + 2 boxes)


def test_dipole_test_flags_moving_star_not_fade():
    rng = np.random.default_rng(1)

    def stamp(comps):
        im = rng.normal(0, 5, (41, 41))
        for x, y, f in comps:
            _add(im, psf.gaussian_psf(2.4), x, y, f)
        return im

    assert detect.dipole_test(stamp([(21.0, 20.0, 300), (19.0, 20.2, -300)]))["dipole"]
    for comps in ([(20.3, 19.8, -250)], [(20.0, 20.0, 400)], [(20.0, 20.0, -40)],
                  [(20.0, 20.0, 300), (24.0, 20.0, -280)]):  # last: two neighbours 4 px apart, not a moving star
        assert not detect.dipole_test(stamp(comps))["dipole"]


# ---------------------------------------------------------------------------------------------- forced photometry


def test_forced_known_measures_masked_positions(core_run, tmp_path):
    d2, prod, cfg = core_run[True]
    out = tmp_path / "SYN" / "T" / "w1"
    out.mkdir(parents=True)
    np.save(out / "D.npy", prod["D"])
    np.save(out / "S.npy", prod["S"])
    np.save(out / "scale.npy", prod["scale"])
    for s_, (r, rv) in prod["refs"].items():
        np.save(out / f"ref_s{s_}.npy", r)
        np.save(out / f"refvar_s{s_}.npy", rv)
        np.save(out / f"psf_s{s_}.npy", prod["psfs"][s_])
    codes = prod["masks"].codes()
    codes[int(SN[1]), int(SN[0])] |= masks.MB_STAR  # pretend it is masked: forced photometry must not care
    np.save(out / "maskbits.npy", codes)
    from oddsky.imaging.stack import seasons
    season = seasons(MJD)
    (out / "meta.json").write_text(json.dumps(dict(wcs=dict(_wcs().to_header()), epochs=list(range(MJD.size)),
                                                   mjd=MJD.tolist(), season=season.tolist(), window=[0, N, 0, N])))
    ra, dec = _wcs().all_pix2world([SN], 0)[0]
    known = pd.DataFrame(dict(name=["AT test"], type=["SN"], disc=["2016-01-01"], ra=[ra], dec=[dec]))
    fk = forced_known(known, tmp_path / "SYN", "T", bands=(1,))
    assert len(fk) == MJD.size and (fk["mask"].str.contains("star")).all()
    on = fk.flux.to_numpy()[12:15]
    assert np.all(on > 300) and np.all(np.abs(fk.flux.to_numpy()[:10]) < 30)
    rs = recall_summary(fk, disc_mjd=MJD[12] - 10)
    assert rs[1]["max_sig"] > 20 and rs[1]["n_sig"] == 3 and rs[1]["both_seasons"]


# ---------------------------------------------------------------------------------------------- runner and targets


def _row(name, ra, dec, a26, dist=1.0):
    return pd.Series({"Name": name, "ra": ra, "dec": dec, "a26": a26, "Dist": dist})


def test_galaxy_from_row_uses_acceptance_geometry():
    m33 = it.galaxy_from_row(_row("MESSIER033", 23.4621, 30.6602, 61.66))
    assert m33.nucleus_mask_arcsec == 40.0  # h0012a used 150"
    m31 = it.galaxy_from_row(_row("MESSIER031", 10.6854, 41.2692, 190.55))
    assert len(m31.extra_masks) == 2  # M32 and NGC 205
    m51 = it.galaxy_from_row(_row("NGC5194", 202.4696, 47.2344, 15.85))  # UNGC's centre, 141" off
    assert abs(m51.dec - 47.195258) < 1e-4
    other = it.galaxy_from_row(_row("UGCX", 100.0, 10.0, 5.0))
    assert other.nucleus_mask_arcsec == pytest.approx(12.0) and other.extra_masks == ()


def test_galaxy_from_row_neighbours_and_bright_sources():
    targets = pd.DataFrame(dict(Name=["NGC5194", "NGC5195", "FAR"], ra=[202.4696, 202.4946, 210.0], dec=[47.1953, 47.2681, 47.0],
                                a26=[15.85, 6.92, 2.0], Dist=[8.6, 8.6, 8.0]))
    bright = pd.DataFrame(dict(galaxy=["NGC5194", "NGC5194", "NGC5195"], ra=[202.4697, 202.6, 202.498],
                               dec=[47.1952, 47.3, 47.266], w1mpro=[8.84, 7.0, 7.5], is_star=[False, True, False]))
    g = it.galaxy_from_row(targets.iloc[0], targets, bright)
    assert g.cores == ((202.4946, 47.2681),)
    assert len(g.bright_sources) == 2 and g.bright_sources[0][3] is False and g.bright_sources[1][3] is True


def test_adopt_centres_corrects_offsets_over_10_arcsec():
    t = pd.DataFrame(dict(Name=["NGC5194", "GOOD", "XSCFAR", "NONED"], ra=[202.4696, 50.0, 60.0, 70.0],
                          dec=[47.2344, 10.0, 20.0, 30.0]))
    ned = pd.DataFrame(dict(ned_status=["ok", "ok", "ok", "unresolved"], ned_ra=[202.46963, 50.0005, 60.008, np.nan],
                            ned_dec=[47.19521, 10.0, 20.0, np.nan], ned_name=["M51a", "G", "X", ""]),
                       index=["NGC5194", "GOOD", "XSCFAR", "NONED"])
    xsc = pd.DataFrame(dict(xsc_ra=[202.469574, 50.0004, 60.0, np.nan], xsc_dec=[47.195259, 10.0, 20.0, np.nan],
                            xsc_id=["a", "b", "c", ""], xsc_k=[5.6, 9.0, 9.0, np.nan]), index=["NGC5194", "GOOD", "XSCFAR", "NONED"])
    out = tg.adopt_centres(t, ned, xsc).set_index("Name")
    assert out.loc["NGC5194", "centre_corrected"] and out.loc["NGC5194", "centre_offset_arcsec"] > 130
    assert abs(out.loc["NGC5194", "dec"] - 47.195258) < 1e-5  # the galaxies.py entry wins
    assert not out.loc["GOOD", "centre_corrected"]  # 1.4": UNGC kept
    assert out.loc["XSCFAR", "centre_source"].startswith("NED")  # XSC 27" from NED: not the same thing
    assert out.loc["XSCFAR", "centre_corrected"]
    assert out.loc["NONED", "centre_source"].startswith("UNGC") and not out.loc["NONED", "centre_corrected"]
    # a NED name match 2 deg away (and the XSC source found round it) must not move the target
    t2 = pd.DataFrame(dict(Name=["CONF"], ra=[206.99], dec=[-53.35]))
    ned2 = pd.DataFrame(dict(ned_status=["ok"], ned_ra=[203.33], ned_dec=[-53.355], ned_name=["other"]), index=["CONF"])
    xsc2 = pd.DataFrame(dict(xsc_ra=[203.33], xsc_dec=[-53.355], xsc_id=["x"], xsc_k=[10.0]), index=["CONF"])
    o2 = tg.adopt_centres(t2, ned2, xsc2).set_index("Name")
    assert not o2.loc["CONF", "centre_corrected"] and "conflict" in o2.loc["CONF", "centre_source"]


def test_by_ungc_name():
    assert by_ungc_name("NGC5194") is GALAXIES["M51"]
    assert by_ungc_name("NGC9999") is None


# ---------------------------------------------------------------------------------------------- v2 score


def _frame(n, **cols):
    base = dict(cls=["step-down"] * n, triage_class=["failed-SN-like"] * n, fsn_shape=["step-down"] * n,
                w1_delta_late_sig=[-6.0] * n, w2_delta_late_sig=[-4.0] * n, w1_delta_neo_sig=[-7.0] * n,
                w2_delta_neo_sig=[-6.0] * n, w1_rise_sig=[np.nan] * n, w2_rise_sig=[np.nan] * n,
                w1_fade_sig=[np.nan] * n, w2_fade_sig=[np.nan] * n, Lbol_pre_est=[1e5] * n, depth_w1=[0.8] * n,
                depth_w2=[0.8] * n, colour_fade=[0.5] * n, colour_up=[np.nan] * n, dipole=[False] * n,
                L_fade_w1=[3e4] * n, rough_max=[1.0] * n, allwise_w1w2=[np.nan] * n)
    base.update(cols)
    return pd.DataFrame(base)


def test_v2_luminosity_floor_roughness_colour():
    df = _frame(5, L_fade_w1=[3e4, 1.5e3, 3e4, 3e4, 4e3], rough_max=[1.0, 1.0, 3.0, 1.0, 1.0],
                allwise_w1w2=[np.nan, np.nan, np.nan, 1.1, np.nan])
    s = mt.fsn_score(df)
    f = mt.fsn_factors_v2(df)
    assert f["f_lfade"][0] > 0.95 and f["f_lfade"][1] < 0.05 and f["f_lfade"][4] == pytest.approx(0.5)
    assert s[1] < 0.05 * s[0]  # an AGB-level loss (1.5e3 L_sun)
    assert s[2] == pytest.approx(s[0] * (1.5 / 3.0) ** 2)  # zig-zag
    assert s[3] == pytest.approx(0.3 * s[0])  # static AGN / dusty AGB colour, anywhere
    # no redness bonus: the colour of the lost light no longer matters
    a, b = mt.fsn_score(_frame(1, colour_fade=[0.0])), mt.fsn_score(_frame(1, colour_fade=[1.0]))
    assert a[0] == pytest.approx(b[0])
    assert mt.fsn_score_v1(_frame(1, colour_fade=[1.0]))[0] == pytest.approx(2 * mt.fsn_score_v1(_frame(1, colour_fade=[0.0]))[0])


def test_v2_proper_motion_and_cutout_dipole():
    df = _frame(4, simbad_otype=["", "PM*", "*", ""], simbad_sep=[np.nan, 1.2, 0.5, np.nan],
                simbad_all=["", 'LP 826-62 [PM*] 1.2"', 'X [*] 0.5"; LP 1 [PM*] 2.4"', ""],
                dipole_cutout=[False, False, False, True])
    assert list(mt.simbad_pm_near(df)) == [False, True, True, False]
    s = mt.fsn_score(df)
    assert s[1] == pytest.approx(0.02 * s[0]) and s[2] == pytest.approx(0.02 * s[0])
    assert s[3] == pytest.approx(0.1 * s[0])
    assert mt.fsn_score_v1(df)[1] == pytest.approx(mt.fsn_score_v1(df)[0])  # v1 ignores both


def test_roughness_feature_separates_zigzag_from_smooth_fade():
    t = 55210 + 182.6 * np.r_[0, 1, 2, np.arange(8, 27)]
    season = np.arange(t.size) % 2
    rng = np.random.default_rng(2)

    def lc(f):
        rows = []
        for b in (1, 2):
            rows.append(pd.DataFrame(dict(band=b, epoch=np.arange(t.size), mjd=t, season=season, flux=f + rng.normal(0, 3, t.size),
                                          err=3.0, ref_flux=100.0)))
        return pd.concat(rows, ignore_index=True)

    smooth = mt.lc_features(lc(np.where(t < 56600, 0.0, -80.0 * (1 - np.exp(-(t - 56600) / 600)))))
    zig = mt.lc_features(lc(-40 + 40 * np.cos(np.arange(t.size) * 2.6)))
    assert smooth[1]["rough"] < 1.6 < zig[1]["rough"]
    # at 100x the S/N: a fade with 4% wiggles stays smooth (amplitude floor), an LPV stays rough
    wig = 1 + 0.04 * np.cos(np.arange(t.size) * 2.6)
    bright_fade = mt.lc_features(lc(np.where(t < 56600, 0.0, -8000.0 * (1 - np.exp(-(t - 56600) / 600))) * wig))
    bright_lpv = mt.lc_features(lc(-4000 + 4000 * np.cos(np.arange(t.size) * 2.6)))
    assert bright_fade[1]["rough"] < 1.5 < bright_lpv[1]["rough"]


# ---------------------------------------------------------------------------------------------- injection


def _host_lc(rng, n=22):
    t = 55210 + 182.6 * np.r_[0, 1, 2, np.arange(8, 8 + n - 3)]
    season = np.arange(t.size) % 2
    return pd.concat([pd.DataFrame(dict(group=1, band=b, epoch=np.arange(t.size), mjd=t, season=season,
                                        flux=rng.normal(0, 2.0, t.size), err=2.0, ref_flux=50.0)) for b in (1, 2)], ignore_index=True)


def test_inject_lc_adds_template_on_reference_scale():
    rng = np.random.default_rng(4)
    lc0 = _host_lc(rng)
    lc = mt.inject_lc(lc0, "BH1", 2012.0, 1000.0)
    w1 = lc[lc.band == 1]
    tot = w1.flux.to_numpy() + w1.ref_flux.to_numpy() - lc0[lc0.band == 1].ref_flux.to_numpy()
    assert tot[0] == pytest.approx(1000.0, abs=8)  # 2010: the whole pre-event star
    assert tot[-1] == pytest.approx(100.0, abs=8)  # 2024: 10% left
    rec = mt.rescore_lc(None, lc)
    assert rec["cls"] in mt.FSN_CLASSES


def test_injection_recovery_ranks_against_population(tmp_path):
    rng = np.random.default_rng(5)
    rows, lcs = [], []
    for k in range(12):
        g = "GALA" if k < 6 else "GALB"
        rows.append(dict(uid=f"{g}|T|{k}", galaxy=g, phot_galaxy=g, tile="T", group=k, has_lc=True, dist_mpc=3.0,
                         triage_class="quiet" if k % 3 else "failed-SN-like", cls="not-variable" if k % 3 else "step-down",
                         fsn_score_v1=0.0 if k % 3 else float(k), fsn_score=0.0 if k % 3 else float(k) / 2, gate_band=1,
                         dipole=False, gaia_foreground=False))
        lc = _host_lc(rng)
        lc["group"] = k
        lcs.append(lc)
    m = pd.DataFrame(rows)
    for g in ("GALA", "GALB"):
        (tmp_path / "T" / g).mkdir(parents=True)
        pd.concat(lcs, ignore_index=True).to_parquet(tmp_path / "T" / g / "lightcurves.parquet")
    inj = mt.injection_recovery(m, tmp_path, n_hosts=4, seed=1, lw1_grid=(3e4,))
    assert set(inj.inj_kind) == {"DS1", "BH1"} and set(inj.inj_xmatch) == {"clean", "inherit"}
    bh1 = inj[(inj.inj_kind == "BH1") & (inj.inj_xmatch == "clean")]
    assert (bh1.triage_class == "failed-SN-like").all()
    assert (bh1.inj_rank_v2 >= 1).all() and (bh1.inj_rank_v2 <= 5).all()
    summ = mt.injection_summary(inj)
    assert summ["all"]["n"] == len(inj)


def test_known_positions_selection():
    targets = pd.DataFrame(dict(Name=["GALA"], ra=[10.0], dec=[20.0], search_diam_arcmin=[10.0]), index=["GALA"])
    objs = pd.DataFrame({"Name": ["SN 2015a", "SN 2005b", "AT 2016c", "SN 2016d"], "ra": [10.01, 10.0, 10.02, 11.0],
                         "dec": [20.0, 20.01, 20.0, 20.0], "Obj. Type": ["SN II", "SN Ia", "Nova", "SN II"],
                         "Discovery Date (UT)": ["2015-03-01", "2005-01-01", "2016-01-01", "2016-01-01"]})
    kp = mt.known_positions(targets, {"GALA": (objs, "ok")})
    assert set(kp.name) == {"SN 2015a", "AT 2016c", "N6946-BH1", "M31-2014-DS1"}


def test_gap_fade_is_step_down_not_transient():
    from oddsky.imaging import metrics

    t = 55210 + 182.6 * np.r_[0, 1, 2, np.arange(8, 27)]
    rng = np.random.default_rng(9)
    f = np.where(t < 55700, 900.0, 90.0) - 90.0 + rng.normal(0, 3, t.size)  # vanished in the 2011-13 gap
    m = metrics.band_metrics(t, f, np.full(t.size, 3.0), np.arange(t.size) % 2)
    assert m["burst_frac"] > 0.8 and m["burst_i0"] == 0
    assert metrics.classify_band(m)[0] == "step-down"
    assert metrics.classify_band(m, gap_fade=False)[0] == "transient"  # the h0012a behaviour
    # a genuine burst in NEOWISE stays a transient
    g = rng.normal(0, 3, t.size)
    g[10:12] += 500
    mg = metrics.band_metrics(t, g, np.full(t.size, 3.0), np.arange(t.size) % 2)
    assert metrics.classify_band(mg)[0] == "transient"


def test_saturation_from_coverage_and_from_real_stars():
    from oddsky.imaging.pipeline import build_mask_set

    st = EpochStack(tile="", band=1, epochs=np.arange(3), mjd=MJD[:3].copy(), img=np.zeros((3, N, N), np.float32),
                    ivar=np.ones((3, N, N), np.float32), wcs=_wcs(), window=(0, N, 0, N))
    st.bitmask = _bitmask()
    ref = np.zeros((N, N), np.float32)
    vf = np.ones((N, N))
    vf[58:63, 58:63] = 0.3  # the core lost most exposures: saturated in the data
    ms = build_mask_set(st, _galaxy(), Config(), ref, np.ones((N, N)), valid_frac=vf)
    assert ms.saturated[60, 60] and ms.det_mask[60, 60] and not ms.lowconf[60, 60]
    assert ms.saturated[int(STAR[1]), int(STAR[0])]  # a genuine star's model saturation stays
    assert ms.codes()[60, 60] & masks.MB_SATURATED
    assert ms.census()["saturated"] > 0
