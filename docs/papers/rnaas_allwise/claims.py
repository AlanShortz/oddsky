"""Receipts for the AllWISE profile-fit research note: `uv run oddsky paper-check docs/papers/rnaas_allwise/claims.py`.
Each number in the text is recomputed here from the tables in this directory (data/ is cut from the H-0016 run
directory by build_receipts.py) and from hunts/H-0016/work."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

DOCUMENT = "../RNAAS_AllWISE_profile_fit_draft.md"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
WORK = "../../../hunts/H-0016/work/"


def build(c):
    from oddsky.data.allwise import expected_w1snr

    stars = c.table("dbf_48_unflagged_stars.csv")
    listed = c.table("dbf_631_listed_sources.csv")
    cols = c.table("data/catalog_columns_48.csv", dtype={"cc_flags": str})
    mep = c.table("data/mep_48.csv")
    nbr = c.table("data/neighbours_48.csv")
    control = c.table("data/control_cone.csv")
    control = control[control.nb == 1]
    offsets = c.table(WORK + "q1_offsets.csv")
    verdict = c.table(WORK + "steps_unwise_verdict.csv")
    valid = c.table(WORK + "allwise_product_validation.csv")
    counts = json.loads((c.root / "data/counts.json").read_text())

    err = stars[stars.klass != "real change"]
    real = stars[stars.klass == "real change"]
    d1 = err.w1_neowise_minus_allwise
    ap_neo = err.w1mag - err.w1_neowise
    usual = err[ap_neo.abs() < 0.2]   # the aperture magnitude is right
    other = err[ap_neo.abs() >= 0.2]  # both AllWISE magnitudes are wrong
    in_window = offsets[(offsets.w1bin >= 8) & (offsets.w1bin <= 14.5)]
    n_clean = 20_560_072 + 22_199_919

    # --- sample and selection
    c.number("4.9 × 10⁷", in_window.n.sum())
    c.every("within 0.03 mag at every magnitude", in_window.d1_med.abs() <= 0.03)
    c.number("19,818", counts["steps_all"])
    c.number("99.4%", 1 - counts["steps_unflagged"] / counts["steps_all"], scale=100)
    c.number("110", counts["steps_unflagged"])
    c.number("48", len(stars))
    c.every("Gaia DR3 parallax above 3σ", verdict.g_parallax_over_error > 3)
    c.number("46", len(err))
    c.number("two are real", len(real))
    c.number("two real changes", len(real))
    c.number("two real stars", len(real))

    # --- the image test
    a = 10 ** (0.4 * stars.w1_neowise_minus_allwise)
    c.span("0.23–2.5 in W1", 7 * a / (a + 6))
    c.number("Forty-six stars", len(err))
    both = pd.concat([err.unwise_ratio_w1, err.unwise_ratio_w2])
    c.every("R between 0.97 and 1.08 in both bands", (both >= 0.97) & (both <= 1.08))
    c.number("For 44 of them", len(usual))
    c.number("to a median 0.02 mag", (usual.w1mag - usual.w1_neowise).abs().median())
    c.span("0.44–1.73 mag", (usual.w1mpro - usual.w1_neowise).abs())
    c.span("0.4–1.7 mag", d1.abs())
    c.number("33 too faint", (usual.w1mpro > usual.w1_neowise).sum())
    c.number("11 too bright", (usual.w1mpro < usual.w1_neowise).sum())
    c.number("The other two", len(other))
    c.span("too bright by 0.5–0.7 mag", pd.concat([other.w1_neowise - other.w1mpro, other.w1_neowise - other.w1mag]))
    far = nbr[nbr.designation.isin(other.designation)]
    c.every("about 2 mag brighter about 12″ away", (far.nb_dG.between(-2.5, -1.5)) & (far.nb_sep.between(11, 13)))

    # --- signature
    c.span("w1snr = 5.4–13.7", err.w1snr)
    c.number("697 clean sources", len(control))
    c.number("47.2 for W1 ≤ 12.5", control[control.w1mpro <= 12.5].w1snr.median())
    c.number("38.9 at W1 = 14.5", control[control.w1mpro.between(14.25, 14.75)].w1snr.median())
    iqr = [np.subtract(*control[(control.w1mpro > lo) & (control.w1mpro <= hi)].w1snr.quantile([0.75, 0.25]))
           for lo, hi in ((8, 12.5), (12.5, 13), (13, 13.5), (13.5, 14), (14, 14.5))]
    c.span("interquartile ranges of 1.3–2.0", iqr)
    c.span("0.35–2.63″", err.allwise_gaia_offset_arcsec)
    c.span("0.35–2.6″", err.allwise_gaia_offset_arcsec)
    c.number("median 0.86″", err.allwise_gaia_offset_arcsec.median())
    c.every("0.05″ for the two real stars", real.allwise_gaia_offset_arcsec.round(2) == 0.05)
    ce = cols[cols.designation.isin(err.designation)]
    c.span("0.10–0.42″", pd.concat([ce.sigra, ce.sigdec]))
    c.number("median of 0.85″ yr⁻¹", np.hypot(ce.pmra, ce.pmdec).median() / 1000)
    per = mep.groupby("designation").agg(sig=("w1sigmpro_ep", "median"), null=("w1sigmpro_ep", lambda s: s.isna().mean()),
                                         neg=("w1flux_ep", lambda s: (s < 0).mean()), chi=("w1rchi2_ep", "median"))
    pe, pr = per[per.index.isin(err.designation)], per[per.index.isin(real.designation)]
    c.every("In the Multiepoch Photometry Table their per-frame fits", [len(pe) == len(err)])
    c.span("0.09–0.27 mag", pe.sig)
    c.every("0.024 and 0.025 mag for the real stars", [sorted(pr.sig.round(3)) == [0.024, 0.025]])
    c.number("a median 15% null uncertainties", pe.null.median(), scale=100)
    c.number("5% negative fluxes", pe.neg.median(), scale=100)
    c.number("median reduced χ² of 3.2", pe.chi.median())
    c.every("All 46 have cc_flags = 0000, nb = 1, na = 0, ext_flg = 0 and w1rchi2 < 3",
            (ce.cc_flags == "0000") & (ce.nb == 1) & (ce.na == 0) & (ce.ext_flg == 0) & (ce.w1rchi2 < 3))

    # --- cause: duplicates in the Reject Table
    rej = c.table("data/reject_entries_48.csv", dtype={"best_use_cntr": str, "cntr": str, "cc_flags": str})
    cat = c.table("data/catalog_tiles_48.csv", dtype={"cntr": str}).set_index("designation")
    status = c.table("data/reject_query_status_48.csv")
    c.every("For 19 of the 46 the AllWISE Reject Table holds a second extraction of the same star from the same Atlas Tile",
            list(status.status == "ok") + [set(status.target) == set(stars.designation)])  # every cone query answered
    w1_neo = stars.set_index("designation").w1_neowise
    full = rej[(rej.w1snr > 25) & ((rej.w1mpro - rej.target.map(w1_neo)).abs() < 0.25) & (rej.sep < 5)
               & rej.target.isin(err.designation) & (rej.coadd_id == rej.target.map(cat.coadd_id))]
    dup = full.sort_values("sep").drop_duplicates("target")
    c.number("For 19 of the 46", len(dup))
    c.span("0.46–2.25″", dup.sep)
    c.number("median 0.97″", dup.sep.median())
    c.span("w1snr = 44.5–49.0", dup.w1snr)
    c.every("w1mpro within 0.08 mag of NEOWISE", (dup.w1mpro - dup.target.map(w1_neo)).abs() <= 0.085)
    c.number("18 are detected in every frame", (dup.w1nm == dup.w1m).sum())
    c.number("18 lie within 0.5″ of the Gaia position", (dup.gaia_sep < 0.5).sum())
    c.number("median 0.06″", dup.gaia_sep.median())
    c.every("All 19 are marked as duplicates not selected for the Catalog (use_src = 0)", dup.use_src == 0)
    first = dup[dup.rel == "r"]   # rejected as the spurious member of a small-separation same-Tile group
    second = dup[dup.rel.isna()]  # not classified as a same-Tile group
    c.number("Two of the 19 good extractions were rejected by the first step", len(first))
    c.every("Two of the 19 good extractions were rejected by the first step", first.target.map(cat.rel) == "s")
    c.number("The other 17 pairs carry no same-Tile mark", len(second))
    c.every("although they lie within 3.9″", second.sep < 3.9)
    c.every("Remaining groups within 2.5″", second.sep < 2.5)
    named = second[second.best_use_cntr == second.target.map(cat.cntr)]
    c.number("For 16 of them best_use_cntr names the catalog entry", len(named))

    def edge(x, y):  # distance to the nearest edge of a 4095-pixel Tile
        return np.minimum.reduce([x, y, 4095 - x, 4095 - y])

    margin = edge(named.target.map(cat.wx), named.target.map(cat.wy)) - edge(named.wx, named.wy)
    c.every("in all 16 is the one farther from the Tile edge", margin > 0)
    c.span("by 0.01–1.2 pixels", margin)
    c.every("A Reject Table entry within 3″ with use_src = 0", (dup.sep < 3) & (dup.use_src == 0))
    c.every("several times the w1snr", dup.w1snr > 3 * dup.target.map(stars.set_index("designation").w1snr))
    fails = c.table(WORK + "allwise_profile_fit_failures.csv", dtype={"cntr": str})
    tiles = fails[fails.tier == "A"].cntr.str.zfill(19).str[:8].value_counts()  # the first eight digits of cntr are the Tile
    c.number("204 of the 631 listed sources", tiles.head(10).sum())
    c.every("lie in 10 Tiles", [tiles.iloc[9] >= 3, tiles.iloc[10] < 3])
    c.number("51 of them in Tile 2719m561", tiles["27190561"])
    c.every("Tile 2719m561", [tiles.index[0] == "27190561"])
    pairs = nbr[nbr.pair == True]  # noqa: E712
    c.number("Thirteen of the 46", len(pairs))
    c.every("within 8.5″ that is no more than 2.5 mag fainter", (pairs.nb_sep < 8.5) & (pairs.nb_dG < 2.5))
    c.number("median separation 6″", pairs.nb_sep.median())
    c.number("four of these are among the 19", dup.target.isin(pairs.designation).sum())
    c.number("For the 27 with no full signal-to-noise Reject Table entry", len(err) - len(dup))
    l40 = c.table("data/reject_entries_listed40.csv")
    c.every("for 14 the Reject Table holds a full signal-to-noise duplicate", [l40.target_cntr.nunique() == 40])
    l40 = l40[l40.designation.notna()]
    sep = 3600 * np.hypot((l40.ra - l40.t_ra) * np.cos(np.radians(l40.t_dec)), l40.dec - l40.t_dec)
    c.number("for 14 the Reject Table", l40[(l40.w1snr > 25) & ((l40.w1mpro - l40.t_w1mag).abs() < 0.25) & (sep < 4)].target_cntr.nunique())
    c.ignore("Same-Tile groups within 3.9″", "radius quoted from the AllWISE Explanatory Supplement, section V.4.b")
    c.ignore("(Section 4)", "cross-reference")
    c.ignore("describe two steps", "the Supplements' procedure")
    c.ignore("rel = 'r'", "flag value")
    c.ignore("Cutri et al. 2012", "citation")
    ecat = cat.loc[err.designation]
    c.number("39 have W1 ph_qual = 'B'", (ecat.ph_qual.str[0] == "B").sum())
    c.number("seven have rel = 's'", (ecat.rel == "s").sum())

    # --- frequency
    c.external("42,759,991", "IRSA TAP COUNT(*) on allwise_p3as_psd with the stated cuts, north 20,560,072 + south 22,199,919 "
                             "(2026-11-03 and 2026-11-05); hunts/H-0016/README.md section 4b")
    c.number("4.3 × 10⁷", n_clean)
    c.number("506,437", counts["discrepant_or_low_snr"])
    c.number("631", len(listed))
    c.number("323 north", (listed.glat > 0).sum())
    c.number("308 south", (listed.glat < 0).sum())
    c.number("1.5 × 10⁻⁵", len(listed) / n_clean)
    c.number("For 591 of them", ((listed.w1mag - listed.w1mpro).abs() > 0.4).sum())
    va = valid[valid.tier == "A"]
    c.number("a random 40", len(va))
    c.number("in 36 and with w1mpro alone in none", ((va.img_minus_ap.abs() < 0.3) & (va.img_minus_pro.abs() > 0.3)).sum())
    c.every("with w1mpro alone in none", ~((va.img_minus_pro.abs() < 0.3) & (va.img_minus_ap.abs() > 0.3)))
    c.number("recovers only 31 of the 46", err.designation.isin(listed.designation).sum())
    c.number("31,549 of the 506,437", counts["fail_two_of_three_tests"])
    c.number("16,749", counts["two_fail_k_favors_profile"])
    c.every("w1mag for 631", [counts["two_fail_k_favors_aperture"] == len(listed)])
    from astropy.coordinates import SkyCoord
    b = SkyCoord(control.ra.values, control.dec.values, unit="deg").galactic.b.deg
    c.every("in one field at b > +80°", b > 80)

    # --- the test applied to the samples
    t2 = err.w1snr < 0.5 * err.w1mpro.apply(expected_w1snr)
    c.every("The 46 were selected with w1nm/w1m ≥ 0.7", err.w1nm / err.w1m >= 0.7)
    c.every("all fail (2)", t2)
    lone = err[err.klass == "catalog error, isolated"]
    c.number("all 33 with no close neighbor fail (4)", len(lone))
    c.every("all 33 with no close neighbor fail (4)", lone.allwise_gaia_offset_arcsec > 0.35)
    k1 = (control.w1mag - control.w1mpro).abs() > 0.3
    k2 = control.w1snr < 0.5 * control.w1mpro.apply(expected_w1snr)
    k3 = control.w1nm / control.w1m < 0.6
    c.every("None of the 697 control sources fails two tests", (k1.astype(int) + k2 + k3) < 2)
    c.number("436 of the 631 fail (3)", (listed.w1nm / listed.w1m < 0.6).sum())

    # --- numerals that are not results
    for text in ("2010–11", "2014–2024", "2010–2020", "2011–2013", "by 2014"):
        c.ignore(text, "dates of the surveys")
    for text in ("Cutri et al. 2013", "al. 2014", "Lang 2014", "Meisner et al. 2022", "Gaia Collaboration 2023"):
        c.ignore(text, "citation")
    for text in ("|b| > 10°", "8 ≤ W1 ≤ 14.5", "at least 12 NEOWISE visits", "first three NEOWISE visits", "below 0.3 mag",
                 "more than 0.4 mag", "fewer than 70%", "cc_flags = 0000, nb = 1 and ext_flg = 0",
                 "|w1mag − w1mpro| > 0.4 or w1snr < 20", "at least two of three", "within 0.4 mag of w1mag"):
        c.ignore(text, "selection cut chosen by the author")
    for text in ("(1) |w1mag − w1mpro| > 0.3", "(2) w1snr", "(3) w1nm/w1m < 0.6", "(4) for a source",
                 "more than 0.35″", "Two failures reject", "fail at least two of tests (1)–(3)", "agrees within 0.3 mag", "Skrutskie et al. 2006", "tests (1) and (2)", "R = 1"):
        c.ignore(text, "definition of the test")
    for text in ("## 1.", "## 2.", "## 3.", "## 4.", "Figure 1", "DRAFT v6", "the two epochs"):
        c.ignore(text, "section, figure or version label; AllWISE and NEOWISE")
    c.review("reviews/referee.md")
