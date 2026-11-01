"""Difference-imaging pipeline (oddsky.imaging) on synthetic unWISE-like images.

A noise + galaxy + star field observed at 22 six-monthly epochs, with the PSF rotating between the
two visit seasons, and three injected sources: a DS1-like star (quiet, +50% over two years, then
fades to nothing), a Mira-like LPV, and a constant star. The pipeline must find the two variables,
recover the injected flux changes, classify them correctly, and raise (almost) nothing else."""

import numpy as np
import pytest

from oddsky.imaging import detect, diff, metrics, photometry, psf
from oddsky.imaging.galaxies import Galaxy
from oddsky.imaging.stack import seasons
from oddsky.imaging.tiles import tile_wcs

N = 160
MJD = 55210 + 182.6 * np.r_[0, 1, 2, np.arange(8, 27)]  # WISE 2010-2011, gap, NEOWISE-R 2014-2024
SIGMA = 1.0  # sky noise per pixel


def elliptical_psf(fwhm=2.3, e=0.12, angle=0.0, size=psf.SIZE):
    """Slightly elongated Gaussian + a faint offset lobe, so the two seasons' PSFs (angle, angle+pi)
    are genuinely different (like WISE's three-fold pattern rotating by 180 deg)."""
    s = fwhm / 2.3548
    r = np.arange(size) - size // 2
    X, Y = np.meshgrid(r, r)
    ca, sa = np.cos(angle), np.sin(angle)
    u, v = ca * X + sa * Y, -sa * X + ca * Y
    g = np.exp(-0.5 * (u**2 / (s * (1 + e)) ** 2 + v**2 / (s * (1 - e)) ** 2))
    g += 0.04 * np.exp(-0.5 * ((u - 3.0) ** 2 + v**2) / (1.2 * s) ** 2)
    return g / g.sum()


def add_point(img, p, x, y, flux):
    h = p.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    img[yi - h : yi + h + 1, xi - h : xi + h + 1] += flux * psf.shifted(p, x - xi, y - yi)


def ds1_curve(t, f0=300.0):
    """Quiet until 2014, +50% by 2016, then fades below quiescence and on to ~0 by 2022."""
    y = np.full_like(t, f0, dtype=float)
    rise = (t >= 56650) & (t < 57650)
    y[rise] = f0 * (1 + 0.5 * (t[rise] - 56650) / 1000)
    fade = t >= 57650
    y[fade] = f0 * 1.5 * np.exp(-(t[fade] - 57650) / 500)
    return y


def mira_curve(t, f0=400.0, amp=250.0, period=412.0):
    return f0 + amp * np.sin(2 * np.pi * t / period)


@pytest.fixture(scope="module")
def synth():
    rng = np.random.default_rng(1)
    season = seasons(MJD)
    psfs = {0: elliptical_psf(angle=0.3), 1: elliptical_psf(angle=0.3 + np.pi)}
    yy, xx = np.mgrid[0:N, 0:N]
    galaxy = 40.0 * np.exp(-np.hypot((xx - 80) / 30.0, (yy - 80) / 15.0))  # bright exponential disk
    stars = [(rng.uniform(15, N - 15), rng.uniform(15, N - 15), rng.uniform(80, 3000)) for _ in range(60)]
    stars += [(20.3, 20.6, 8000.0), (140.2, 30.4, 6000.0), (30.7, 135.1, 7000.0)]  # bright PSF stars
    src = {"ds1": (95.3, 84.6), "mira": (60.4, 70.2), "const": (110.7, 60.3)}
    truth = {"ds1": ds1_curve(MJD), "mira": mira_curve(MJD), "const": np.full(MJD.size, 500.0)}
    img = np.empty((MJD.size, N, N), np.float32)
    ivar = np.full_like(img, 1 / SIGMA**2)
    for i in range(MJD.size):
        p = psfs[int(season[i])]
        im = galaxy.copy()
        dx, dy = rng.normal(0, 0.08, 2)  # astrometric jitter between epochs
        for x, y, f in stars:
            add_point(im, p, x + dx, y + dy, f)
        for k, (x, y) in src.items():
            add_point(im, p, x + dx, y + dy, truth[k][i])
        im += rng.normal(0, SIGMA, im.shape)
        img[i] = im
    return dict(img=img, ivar=ivar, season=season, psfs=psfs, src=src, truth=truth)


@pytest.fixture(scope="module")
def run(synth):
    img, ivar, season = synth["img"], synth["ivar"], synth["season"]
    refs = diff.references(img, ivar, season)
    floors = {k: diff.residual_floor(r) for k, (r, _) in refs.items()}
    D = np.empty_like(img)
    S = np.empty_like(img)
    scales = np.empty(img.shape, np.float32)
    dets = []
    for i in range(img.shape[0]):
        r, rv = refs[int(season[i])]
        D[i], S[i], _ = diff.difference(img[i], ivar[i], r, rv, block=N, floor=floors[int(season[i])])
        D[i] -= diff.background_mesh(D[i], S[i], 24)
        snr, F, E, c = detect.snr_map(D[i], S[i], synth["psfs"][int(season[i])], box=40)
        scales[i] = c
        x, y, v = detect.find_peaks(snr, 5.0)
        dets += [(i, xx, yy, vv, season[i]) for xx, yy, vv in zip(x, y, v, strict=True)]
    return dict(refs=refs, D=D, S=S, scales=scales, dets=np.array(dets))


def test_gaussian_psf_fwhm():
    assert psf.fwhm(psf.gaussian_psf(2.3)) == pytest.approx(2.3, rel=0.05)


def test_empirical_psf_matches_input(synth):
    ref = diff.references(synth["img"], synth["ivar"], synth["season"])[0][0]
    stars = psf.find_stars(ref, np.ones_like(ref) * 12, snr_min=30, isolation=6)
    assert len(stars) >= 5
    p = psf.build_psf(ref, stars)
    truth = synth["psfs"][0]
    assert np.abs(p - truth).sum() < 0.25  # L1 distance between normalised PSFs
    assert psf.fwhm(p) == pytest.approx(psf.fwhm(truth), rel=0.1)


def test_kernel_recovers_scale_and_shift():
    rng = np.random.default_rng(3)
    ref = np.zeros((96, 96))
    p = psf.gaussian_psf(2.3)
    for _ in range(40):
        add_point(ref, p, rng.uniform(14, 82), rng.uniform(14, 82), rng.uniform(200, 2000))
    img = 1.07 * psf.shifted(np.pad(ref, 0), 0.3, -0.2) + 5.0  # shifted, scaled, offset
    img = img + rng.normal(0, 0.5, img.shape)
    K, b = diff.fit_kernel(ref, img, np.full(img.shape, 4.0))
    assert K.sum() == pytest.approx(1.07, abs=0.02)
    assert b == pytest.approx(5.0, abs=0.3)
    model, _ = diff.apply_kernel(ref, np.zeros_like(ref), K, b)
    resid = (img - model)[10:-10, 10:-10]
    assert resid.std() < 0.7  # ~ the injected noise


def test_difference_noise_is_calibrated(run, synth):
    """Away from sources, calibrated S/N should be ~unit normal."""
    i = 5
    s = int(synth["season"][i])
    snr, *_ = detect.snr_map(run["D"][i], run["S"][i], synth["psfs"][s], box=40)
    core = snr[20:-20, 20:-20]
    mad = 1.4826 * np.nanmedian(np.abs(core - np.nanmedian(core)))
    assert 0.8 < mad < 1.25


def test_variables_detected_in_many_epochs(run, synth):
    d = run["dets"]
    for name in ("ds1", "mira"):
        x, y = synth["src"][name]
        near = np.hypot(d[:, 1] - x, d[:, 2] - y) < 1.5
        assert len(set(d[near, 0].astype(int))) >= 5, name
    x, y = synth["src"]["const"]
    assert not (np.hypot(d[:, 1] - x, d[:, 2] - y) < 1.5).any()


def test_few_false_detections(run, synth):
    d = run["dets"]
    real = np.zeros(len(d), bool)
    for x, y in [synth["src"]["ds1"], synth["src"]["mira"]]:
        real |= np.hypot(d[:, 1] - x, d[:, 2] - y) < 2.5
    fake = d[~real]
    # pure-noise 5-sigma peaks: about one per epoch over this 160x160 field (heavier tails than
    # Gaussian: the reference's own noise is shared by all epochs of a season) ...
    assert len(fake) < 2 * len(MJD)
    # ... but none repeats at one position in both seasons (the candidate criterion)
    if len(fake):
        lab = detect.group(fake[:, 1] / 3600 * 2.75, fake[:, 2] / 3600 * 2.75 + 10, 4.0)
        for g in np.unique(lab):
            assert len(set(fake[lab == g, 4].astype(int))) < 2


def test_forced_photometry_recovers_injected_changes(run, synth):
    season = synth["season"]
    for name in ("ds1", "mira"):
        x, y = synth["src"][name]
        sc = run["scales"][:, int(round(y)), int(round(x))]
        f, e = photometry.forced_lightcurve(run["D"], run["S"], synth["psfs"], season, x, y, sc)
        truth = synth["truth"][name]
        # reference = per-season median, so compare after removing each season's median
        resid = []
        for s in (0, 1):
            m = season == s
            resid.append((f[m] - np.median(f[m])) - (truth[m] - np.median(truth[m])))
        resid = np.concatenate(resid)
        assert np.median(np.abs(resid)) < 3 * np.median(e), name
        assert np.median(e) < 25


def test_reference_flux_on_galaxy(run, synth):
    r, rv = run["refs"][0]
    x, y = synth["src"]["const"]
    f, e = photometry.reference_flux(r, rv, synth["psfs"][0], x, y)
    assert f == pytest.approx(500.0, rel=0.1)


def test_classification_end_to_end(run, synth):
    season = synth["season"]
    out = {}
    for name in ("ds1", "mira", "const"):
        x, y = synth["src"][name]
        sc = run["scales"][:, int(round(y)), int(round(x))]
        f, e = photometry.forced_lightcurve(run["D"], run["S"], synth["psfs"], season, x, y, sc)
        rf = {s: photometry.reference_flux(*run["refs"][s], synth["psfs"][s], x, y)[0] for s in (0, 1)}
        m = metrics.band_metrics(MJD, metrics.align_seasons(f, season, rf), e, season)
        out[name] = metrics.classify(m, {})
    assert out["ds1"][0] in ("rise-then-fade", "fading")
    assert out["mira"][0] == "lpv-like"
    assert out["const"][0] == "not-variable"
    assert out["ds1"][1] > out["mira"][1]


def test_metrics_on_clean_curves():
    t = MJD
    e = np.full(t.size, 10.0)
    ds1 = ds1_curve(t) - 300
    m = metrics.band_metrics(t, ds1, e)
    assert m["n_turns"] == 1 and m["eta"] < 0.6
    assert m["rise_sig"] > 5 and m["fade_sig"] > 5
    assert metrics.classify(m, {})[0] == "rise-then-fade"
    lpv = mira_curve(t) - 400
    ml = metrics.band_metrics(t, lpv, e)
    assert ml["eta"] > 1.2 and ml["n_turns"] >= 4
    assert metrics.classify(ml, {})[0] == "lpv-like"
    fade = np.where(t > 57000, -200.0 * (1 - np.exp(-(t - 57000) / 800)), 0.0)
    assert metrics.classify(metrics.band_metrics(t, fade, e), {})[0] == "fading"


def test_short_transient_class():
    t = MJD
    e = np.full(t.size, 10.0)
    sn = np.where(np.abs(t - 57900) < 200, 3000.0, 0.0)  # one or two epochs, then gone
    m = metrics.band_metrics(t, sn, e)
    assert m["burst_frac"] > 0.8
    assert metrics.classify(m, {})[0] == "transient"


def test_background_mesh_removes_large_scale_but_keeps_points():
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:256, 0:256]
    smooth = 20 * np.sin(xx / 40.0) * np.cos(yy / 50.0)  # arcminute-scale galaxy residual
    pt = np.zeros((256, 256))
    add_point(pt, psf.gaussian_psf(2.3), 128.2, 127.7, 500.0)
    D = (smooth + pt + rng.normal(0, 1, pt.shape)).astype(np.float32)
    S = np.ones_like(D)
    bkg = diff.background_mesh(D, S, 24)
    resid = D - bkg
    assert np.std((resid - pt)[30:-30, 30:-30]) < 0.25 * np.std(smooth)  # >75% of the structure removed
    f, _ = photometry.forced_flux(resid, S, psf.gaussian_psf(2.3), 128.2, 127.7)
    assert f == pytest.approx(500, rel=0.08)


def test_zigzag_and_von_neumann():
    assert metrics.zigzag_turns(np.array([0, 1, 2, 3, 2, 1, 0.0]), 0.5) == 1
    assert metrics.zigzag_turns(np.array([0, 2, 0, 2, 0, 2.0]), 0.5) == 4
    assert metrics.von_neumann(np.arange(20.0)) < 0.1
    rng = np.random.default_rng(0)
    assert 1.5 < metrics.von_neumann(rng.normal(size=2000)) < 2.5


def test_seasons_alternate():
    assert seasons(MJD).tolist()[:3] == [0, 1, 0]
    assert seasons(MJD)[3] == 0  # 2014 Jan is 8 half-years after 2010 Jan


def test_group_links_across_epochs():
    ra = np.array([10.0, 10.0 + 1 / 3600, 10.0 + 2 / 3600, 10.1])
    dec = np.array([41.0, 41.0, 41.0, 41.0])
    lab = detect.group(ra, dec, 4.0)
    assert lab[0] == lab[1] == lab[2] != lab[3]


def test_galaxy_ellipse_and_tile_wcs():
    g = Galaxy("T", 10.0, 40.0, 60.0, 0.5, 30.0, 1.0, search_scale=1.0)
    assert g.ellipse_r(10.0, 40.0) == pytest.approx(0)
    ra, dec = g.boundary(36)
    assert np.allclose(g.ellipse_r(ra, dec), 1.0, atol=1e-3)
    w = tile_wcs(10.0, 40.0)
    x, y = w.all_world2pix([[10.0, 40.0]], 0)[0]
    assert (x, y) == pytest.approx((1023.5, 1023.5))


# ---------------------------------------------------------------------------------------------
# Referee round (2026-11-01): stacked channel, leave-one-out references, absolute seasons, Gaia
# IDs, and a 2010-vs-NEOWISE PSF / zero-point change in the synthetic sky.

from oddsky.imaging import crossmatch  # noqa: E402
from oddsky.imaging.pipeline import Config, analyse_stack, candidates_from  # noqa: E402
from oddsky.imaging.stack import EpochStack  # noqa: E402

NS = 120
BH1_AMP = 16.0  # ~4.4 sigma per epoch: below the single-epoch threshold, ~7 sigma stacked


@pytest.fixture(scope="module")
def stack_run():
    """22 epochs; the three 2010-11 epochs have a broader PSF (FWHM 2.55 vs 2.3) and read 2% bright
    (unTimely's first-pass offset); a BH1-like source is present ONLY in 2010-11; a constant star
    and a bright star test for spurious 2010-vs-NEOWISE residuals."""
    rng = np.random.default_rng(7)
    from astropy.wcs import WCS

    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [10.0, 40.0]
    w.wcs.crpix = [NS / 2 + 0.5, NS / 2 + 0.5]
    w.wcs.cdelt = [-2.75 / 3600, 2.75 / 3600]
    yy, xx = np.mgrid[0:NS, 0:NS]
    galaxy = 25.0 * np.exp(-np.hypot((xx - 60) / 25.0, (yy - 60) / 14.0))
    stars = [(rng.uniform(14, NS - 14), rng.uniform(14, NS - 14), rng.uniform(80, 1500)) for _ in range(30)]
    stars += [(20.3, 99.6, 6000.0), (100.2, 20.4, 5000.0), (95.4, 95.7, 4000.0)]
    src = {"bh1": (40.4, 70.3), "const": (80.6, 45.2)}
    img = np.empty((MJD.size, NS, NS), np.float32)
    for i in range(MJD.size):
        early = MJD[i] < 55700
        p = elliptical_psf(fwhm=2.55 if early else 2.3, angle=0.3 + np.pi * (i % 2))
        im = galaxy.copy()
        for x, y, f in stars:
            add_point(im, p, x, y, f)
        add_point(im, p, *src["const"], 600.0)
        if early:
            add_point(im, p, *src["bh1"], BH1_AMP)
        im *= 1.02 if early else 1.0
        img[i] = im + rng.normal(0, SIGMA, im.shape)
    st = EpochStack(tile="", band=1, epochs=np.arange(MJD.size), mjd=MJD.copy(), img=img,
                    ivar=np.full_like(img, 1 / SIGMA**2), wcs=w, window=(0, NS, 0, NS))
    gal = Galaxy("SYN", 10.0, 40.0, 30.0, 1.0, 0.0, 5.0, nucleus_mask_arcsec=1.0, search_scale=1.0)
    cfg = Config(box=40, block=NS)
    dets, prod = analyse_stack(st, gal, cfg)
    return dict(st=st, dets=dets, prod=prod, src=src, stars=stars, cfg=cfg, wcs=w)


def _near(d, x, y, r=1.5):
    return np.hypot(d.x - x, d.y - y) < r


def test_stack_channel_finds_bh1_like_fader_blind(stack_run):
    d, (x, y) = stack_run["dets"], stack_run["src"]["bh1"]
    ep = d[(d.channel == "epoch") & _near(d, x, y)]
    stk = d[(d.channel == "neo-early") & _near(d, x, y)]
    assert len(stk) == 1 and stk.snr.iloc[0] < -5  # faded: NEOWISE minus 2010 is negative
    assert ep.season.nunique() < 2  # the single-epoch channel alone could not make it a candidate
    c = candidates_from(d, stack_run["cfg"])
    ra, dec = stack_run["wcs"].all_pix2world([[x, y]], 0)[0]
    hit = c[np.hypot((c.ra - ra) * np.cos(np.radians(dec)), c.dec - dec) * 3600 < 4]
    assert len(hit) == 1 and hit.channel.iloc[0] in ("stack", "both")


def test_no_spurious_stack_detections_from_2010_psf_and_zeropoint(stack_run):
    d = stack_run["dets"]
    stk = d[d.channel != "epoch"]
    bx, by = stack_run["src"]["bh1"]
    others = stk[~_near(stk, bx, by, 2.5)]
    assert len(others) == 0, others[["x", "y", "snr", "channel"]]


def test_season_combined_stack_requires_both_seasons(stack_run):
    from oddsky.imaging.pipeline import stack_channel

    prod = stack_run["prod"]
    D, S, st = prod["D"], prod["S"], stack_run["st"]
    # an artefact present in ONE season's NEOWISE epochs only must not pass
    acc = {}
    x, y = 60, 30
    for i in range(st.n):
        s = int(st.season[i])
        d = D[i].copy()
        if s == 0 and st.mjd[i] > 56600:
            add_point(d, prod["psfs"][0], x, y, 40.0)
        w = 1 / S[i] ** 2
        for name, m in {"early": st.mjd[i] < 55700, "neo": st.mjd[i] > 56600, "late": st.mjd[i] > st.mjd.max() - 550}.items():
            if m:
                num, den = acc.get((s, name), (np.zeros_like(d), np.zeros_like(d)))
                acc[(s, name)] = (num + np.nan_to_num(d) * w, den + w)
    out = stack_channel(acc, prod["psfs"], np.zeros_like(D[0], bool), np.zeros_like(D[0], bool), stack_run["cfg"])
    keep = out["neo-early"][3]
    assert not any(np.hypot(k[0] - x, k[1] - y) < 2 for k in keep)


def test_loo_medians_match_brute_force():
    rng = np.random.default_rng(0)
    img = rng.normal(size=(9, 6, 7)).astype(np.float32)
    iv = np.ones_like(img)
    iv[2, 1, 1] = 0
    iv[4, 0, :] = 0
    out = diff.loo_medians(img, iv)
    for i in range(9):
        for y in range(6):
            for x in range(7):
                sel = [j for j in range(9) if j != i and iv[j, y, x] > 0]
                assert out[i, y, x] == pytest.approx(np.median(img[sel, y, x]), abs=1e-6)


def test_loo_reference_does_not_absorb_a_transient():
    """With few epochs, a self-including median eats part of a one-epoch burst; leave-one-out not."""
    n = 5
    img = np.zeros((n, 1, 1), np.float32)
    img[:, 0, 0] = [0, 1, 2, 10, 3]  # epoch 3 bursts
    iv = np.ones_like(img)
    med_all = np.median(img[:, 0, 0])
    loo = diff.loo_medians(img, iv)[3, 0, 0]
    assert img[3, 0, 0] - loo > img[3, 0, 0] - med_all  # 10 - 1.5 > 10 - 2


def test_absolute_seasons_agree_across_tiles_and_are_not_tile_relative():
    from oddsky.imaging.stack import seasons

    m31 = (10.68, 41.27)
    a = 55211.2 + 182.6 * np.arange(6)  # first epoch Jan 2010
    b = a[1:]  # a tile whose first epoch is Jul 2010
    sa, sb = seasons(a, *m31), seasons(b, *m31)
    assert np.array_equal(sa[1:], sb)  # absolute: same label for the same visit
    assert not np.array_equal(seasons(b), sb)  # tile-relative labelling would flip
    assert sa[0] == 0 and sa[1] == 1  # M31: Sun 90 deg behind in Jan, ahead in Jul
    # two nearby positions (adjacent tiles) agree
    assert np.array_equal(seasons(a, 10.68, 41.27), seasons(a, 12.0, 42.4))


def test_gaia_source_id_stays_a_string():
    csv = "source_id,ra,dec,g,bp_rp,parallax,parallax_over_error,pmra,pmra_error,pmdec,pmdec_error,phot_variable_flag,ruwe,p_quasar,p_galaxy\n" \
          "380754490083950080,9.336,40.2771,16.63,0.15,-0.12,-2.0,0.21,0.05,0.0,0.05,VARIABLE,1.03,0.0,0.0\n" \
          "369120145234465024,10.5671,40.3267,16.85,1.06,0.1,1.0,0.0,0.1,0.0,0.1,VARIABLE,1.1,1.0,0.0\n"
    g = crossmatch.read_gaia_csv(csv)
    assert g.source_id.tolist() == ["380754490083950080", "369120145234465024"]
    import pandas as pd

    cands = pd.DataFrame(dict(group=[1, 2, 3], ra=[9.336, 10.5671, 11.0], dec=[40.2771, 40.3267, 42.0]))
    x = crossmatch.nearest(cands, g)
    assert x.gaia_id.iloc[0] == "380754490083950080"
    assert bool(x.quasar.iloc[1]) and not bool(x.quasar.iloc[0])
    assert pd.isna(x.gaia_id.iloc[2])
    assert crossmatch.agn_colour_flag([100.0], [250.0], [1.2])[0]  # W1-W2 = 0.99 outside D25
    assert not crossmatch.agn_colour_flag([100.0], [250.0], [0.5])[0]


def test_classification_uses_one_band_and_reports_both():
    t = MJD
    e = np.full(t.size, 10.0)
    m_ds1 = metrics.band_metrics(t, ds1_curve(t) - 300, e)
    m_lpv = metrics.band_metrics(t, 3 * (mira_curve(t) - 400), e)
    r = metrics.classify_bands(m_ds1, m_lpv)  # W2 (LPV) has the larger chi2 -> it gates
    assert r["gate_band"] == 2 and r["cls"] == "lpv-like" and r["cls_w1"] == "rise-then-fade"
    assert not r["band_agree"]


def test_step_class_for_quiet_gap_fader():
    t = MJD
    e = np.full(t.size, 10.0)
    f = np.where(t < 55700, 40.0, 0.0)  # 4 sigma per epoch, only in 2010-11: chi2_r ~ 2, gate fails
    m = metrics.band_metrics(t, f, e)
    assert m["chi2r"] < 5
    assert m["delta_neo_sig"] < -5
    assert metrics.classify_band(m)[0] == "step-down"
