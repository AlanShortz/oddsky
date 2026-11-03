"""TNS packet 2026-11: machine-readable fill files for the TNS AT-report form (https://www.wis-tns.org/reports/at),
one per ready candidate, with the exact element ids and option values used when OS-0030 was filled (2026-11-02,
filed as AT 2020afkm): text inputs set by id; selects set by option value; the second photometry row appears after
clicking #photometry-add-more; the related file goes into #edit-related-file-0 with its comment in
#edit-related-files-related-files-group-0-related-file-comments.

NOTHING IS SUBMITTED by this script or by these files. They are inputs for a human-supervised fill.

    uv run python hunts/H-0012/drafts/tns_packet_2026-11/scripts/make_fill.py
Output: hunts/H-0012/drafts/tns_packet_2026-11/fill_<name>.json
"""
import json
from pathlib import Path

PK = Path(__file__).resolve().parents[1]
N = json.loads((PK / "numbers.json").read_text())
CREDIT = "unWISE time-resolved coadds (NEO11 version, courtesy A. Meisner; Meisner, Lang & Schlegel 2018)"
OBS = "WISE/NEOWISE (NASA/JPL/IPAC)"

# option values of the select elements, as read from the live form on 2026-11-02 for OS-0030
SEL = {"arcsec": "arcsec", "None": "0", "Other - Undefined": "0", "ABMag": "1", "3.4-WISE": "45", "4.6-WISE": "46",
       "Other - Other": "0"}
# IRAC options (NGC 4945, Spitzer discovery): NOT read from the live AT form. They come from the TNS values mirror
# (HeloiseS/tns_wizard tns_codes.json, committed 2026-09-02, copy in
# ~/oddsky-runs/imaging/scratch/tns-validation-os0030/policy/gh/), the same source as 45/46, which the live form
# confirmed for OS-0030: instruments "193": "SST - IRAC"; filters "40": "3.6-Spitzer IRAC", "41": "4.5-Spitzer IRAC".
SEL.update({"SST - IRAC": "193", "3.6-Spitzer IRAC": "40", "4.5-Spitzer IRAC": "41"})
EXPECT = {"edit-ra-units": "arcsec", "edit-decl-units": "arcsec", "edit-reporting-groupid": "None [0]",
          "edit-data-source-groupid": "None [0]", "edit-at-type": "Other - Undefined [0]",
          "edit-non-detection-flux-units": "ABMag [1]", "edit-non-detection-filter-value": "3.4-WISE [45]",
          "edit-non-detection-instrument-value": "Other - Other [0]"}

REMARKS = {
    "M81_OS-0035": (
        f"Mid-infrared eruption found in archival WISE/NEOWISE data by Oddsky (oddsky.ai): difference imaging of the {CREDIT} "
        "against a 2014.8-2023.2 reference. Nothing at this position in 18 W1/W2 epochs from 2014-10 to 2023-03-27. "
        "First detected 2023-10-23 at W1 = 18.18 +- 0.07 and W2 = 18.05 +- 0.12 AB; on 2024-03-28, the last NEOWISE epoch "
        "here, W1 = 16.71 +- 0.02 and W2 = 16.36 +- 0.02 AB, still rising. Magnitudes are of the difference flux; the "
        "flux-scale systematic is about 0.1 mag. An earlier infrared event at the same position: public Spitzer/IRAC 3.6 um "
        "images show +0.22 mJy on 2009-11-25, declining to +0.13 mJy by 2010-04/06, after a flat 2003-2005, and WISE 2010 "
        "was still above the 2014-2023 level. The source lies in the HII region [HAE2008] 7; Gaia DR3 1070474934439610752 "
        "(G = 20.25, BP-RP = 0.37) is 0.28\" away. No ZTF alert object within 35\". ATLAS forced photometry shows no "
        "brightening at the WISE epochs (3-sigma limits c > 21.3, o > 21.2 AB). 351\" NW of the centre of M81. No spectrum."),
}
REMARKS_NGC4945 = (
    "Mid-infrared transient found by Oddsky (oddsky.ai) in archival WISE/NEOWISE data, by difference imaging of the "
    f"{CREDIT}, and measured in public Spitzer/IRAC images from IRSA (SPIRITS programmes 13053 and 14089, PI M. Kasliwal). "
    "The discovery point is the earliest >= 5 sigma detection: IRAC [3.6] = 20.09 +- 0.10 AB (+33 +- 3 uJy) on 2018-06-02, "
    "against the median of 12 flat 2013-2016 epochs; [3.6] was +17 +- 4 uJy (3.9 sigma) on 2017-10-03. Later IRAC: "
    "[4.5] = 19.65 +- 0.11 AB on 2018-11-23; [3.6] = 18.13 +- 0.02 AB on 2019-07-02. WISE (difference flux, AB): flat in "
    "11 epochs from 2010 to 2017-07; first >= 5 sigma on 2019-01-27 at W1 = 18.97 +- 0.10, W2 = 18.80 +- 0.22; peak on "
    "2022-07-07 at W1 = 16.52 +- 0.02, W2 = 16.71 +- 0.04; fading to W1 = 18.20 +- 0.09 by 2024-07-06, the last NEOWISE "
    "epoch; flux-scale systematic about 0.1 mag. The position is the IRAC centroid of the brightening, 0.8\" from the WISE "
    "centroid and 0.2\" from a 4.5 um source of 41 uJy with no 3.6 um detection in the cryogenic-era Spitzer SEIP "
    "catalogue (SSTSL2 J130552.71-492458.3). No Gaia DR3 source within 6\". ATLAS forced photometry shows no optical "
    "counterpart at the infrared peak (3-sigma limits c > 22.0, o > 21.0 AB). 309\" NE of the centre of NGC 4945. "
    "No spectrum.")
SP_OBS = "Spitzer Space Telescope (NASA/JPL-Caltech); SPIRITS, PI M. Kasliwal; data from IRSA"

SPEC = {
    "M81_OS-0035": dict(host="NGC 3031", z="", internal="Oddsky OS-0035", nd_ep=20, d_ep=21, ref="2014.8-2023.2",
                        exp_nd=161.7, exp_w1=130.9, exp_w2=123.2,
                        fig="M81_OS-0035_summary.png",
                        fig_comment="Discovery summary: unWISE W1/W2 difference light curve 2010-2024 with Spitzer/IRAC 2003-2019, "
                                    "and W1/W2 difference stamps at the last non-detection, discovery and latest epoch (Oddsky case OS-0035)."),
    "NGC4945_obs3": dict(host="NGC 4945", z="0.001878", internal="Oddsky H0012-NGC4945-1", nd_ep=12, d_ep=13, ref="2010-2017",
                         exp_nd=77.0, exp_w1=192.5, exp_w2=200.2,
                         fig="NGC4945_obs3_summary.png",
                         fig_comment="Discovery summary: Spitzer/IRAC (SPIRITS) and unWISE W1/W2 difference light curves 2007-2024 "
                                     "(IRAC discovery 2018-06-02 marked), and WISE W1/W2 difference stamps at the WISE last non-detection, "
                                     "first WISE detection and W1 peak (Oddsky H0012-NGC4945-1)."),
}


def frac_day(t):
    """'2023-10-22 16:22' -> '2023-10-22.68'"""
    d, hm = t.split(" ")
    h, m = hm.split(":")[:2]
    return f"{d}.{round((int(h) + int(m) / 60) / 24 * 100):02d}"


def build(lab, remarks):
    n, s = N[lab], SPEC[lab]
    p = n["position"]
    d, nd = n["discovery"], n["last_nondetection"]
    w1, w2, nw1 = d["phot"]["W1"], d["phot"]["W2"], nd["phot"]["W1"]
    nd_comment = (f"Instrument=WISE (NEOWISE-R reactivation), unWISE neo11 epochal coadd (epoch {s['nd_ep']}), forced PSF "
                  f"photometry on a difference image at the source, measured flux {nw1['uJy']:+.1f} +- "
                  f"{nw1['e_uJy']:.1f} uJy ({nw1['snr']:.1f} sigma). Limit is 5 sigma, AB.")
    if lab == "NGC4945_obs3":
        nd_comment += (" The rise is slow: the previous epoch (2018-01-27) has W1 +40 +- 11 uJy (3.7 sigma); "
                       f"W2 here {nd['phot']['W2']['uJy']:+.1f} +- {nd['phot']['W2']['e_uJy']:.1f} uJy, 5-sigma limit "
                       f"{nd['phot']['W2']['lim5_AB']:.2f} AB.")
    else:
        nd_comment += (f" W2 {nd['phot']['W2']['uJy']:+.1f} +- {nd['phot']['W2']['e_uJy']:.1f} uJy, 5-sigma limit "
                       f"{nd['phot']['W2']['lim5_AB']:.2f} AB.")
    t0, t1 = frac_day(d["time"]["utc_first"]), frac_day(d["time"]["utc_last"])
    p0 = (f"Instrument=WISE (NEOWISE-R), unWISE neo11 epochal coadd (epoch {s['d_ep']}; exposures {t0} to {t1[5:]}). "
          f"Difference flux {w1['uJy']:.1f} +- {w1['e_uJy']:.1f} uJy ({w1['snr']:.0f} sigma) vs {s['ref']} reference. "
          f"Vega {w1['Vega']:.2f}. Flux-scale systematic ~0.1 mag.")
    p1 = (f"Instrument=WISE (NEOWISE-R), unWISE neo11 epoch {s['d_ep']}. Difference flux {w2['uJy']:.1f} +- "
          f"{w2['e_uJy']:.1f} uJy ({w2['snr']:.1f} sigma). Vega {w2['Vega']:.2f}.")

    def row(i, mag, err, filt, exp, com):
        g = f"edit-photometry-photometry-group-{i}-"
        return [dict(id=g + "obsdate", type="text", value=d["time"]["utc_mean"]),
                dict(id=g + "flux", type="text", value=f"{mag:.2f}"),
                dict(id=g + "flux-error", type="text", value=f"{err:.2f}"),
                dict(id=g + "flux-units", type="select", value=SEL["ABMag"], label="ABMag"),
                dict(id=g + "filter-value", type="select", value=SEL[filt], label=filt),
                dict(id=g + "instrument-value", type="select", value=SEL["Other - Other"], label="Other - Other"),
                dict(id=g + "exptime", type="text", value=f"{exp:.1f}"),
                dict(id=g + "observer", type="text", value=OBS),
                dict(id=g + "comments", type="text", value=com)]

    fields = [
        dict(id="edit-ra-value", type="text", value=p["ra_hms"]),
        dict(id="edit-ra-error", type="text", value=f"{p['err_arcsec_quoted']}"),
        dict(id="edit-ra-units", type="select", value=SEL["arcsec"], label="arcsec"),
        dict(id="edit-decl-value", type="text", value=p["dec_dms"]),
        dict(id="edit-decl-error", type="text", value=f"{p['err_arcsec_quoted']}"),
        dict(id="edit-decl-units", type="select", value=SEL["arcsec"], label="arcsec"),
        dict(id="edit-reporting-groupid", type="select", value=SEL["None"], label="None"),
        dict(id="edit-data-source-groupid", type="select", value=SEL["None"], label="None"),
        dict(id="edit-reporter", type="text", value="Alan Shortz (Oddsky)"),
        dict(id="edit-discovery-datetime", type="text", value=d["time"]["utc_mean"]),
        dict(id="edit-at-type", type="select", value=SEL["Other - Undefined"], label="Other - Undefined"),
        dict(id="edit-host-name", type="text", value=s["host"]),
        dict(id="edit-host-redshift", type="text", value=s["z"]),
        dict(id="edit-internal-name", type="text", value=s["internal"]),
        dict(id="edit-remarks", type="text", value=remarks),
        dict(id="edit-non-detection-obsdate", type="text", value=nd["time"]["utc_mean"]),
        dict(id="edit-non-detection-limiting-flux", type="text", value=f"{nw1['lim5_AB']:.2f}"),
        dict(id="edit-non-detection-flux-units", type="select", value=SEL["ABMag"], label="ABMag"),
        dict(id="edit-non-detection-filter-value", type="select", value=SEL["3.4-WISE"], label="3.4-WISE"),
        dict(id="edit-non-detection-instrument-value", type="select", value=SEL["Other - Other"], label="Other - Other"),
        dict(id="edit-non-detection-exptime", type="text", value=f"{s['exp_nd']:.1f}"),
        dict(id="edit-non-detection-observer", type="text", value=OBS),
        dict(id="edit-non-detection-comments", type="text", value=nd_comment),
    ]
    fields += row(0, w1["AB"], w1["e_AB"], "3.4-WISE", s["exp_w1"], p0)
    fields.append(dict(click="#photometry-add-more", wait_for="#edit-photometry-photometry-group-1-obsdate"))
    fields += row(1, w2["AB"], w2["e_AB"], "4.6-WISE", s["exp_w2"], p1)
    fields += [dict(id="edit-related-file-0", type="file", value=s["fig"]),
               dict(id="edit-related-files-related-files-group-0-related-file-comments", type="text", value=s["fig_comment"])]
    return dict(
        status="DRAFT - NOT SUBMITTED. Do not click #edit-submit without Alan's explicit go-ahead.",
        form_url="https://www.wis-tns.org/reports/at",
        precedent="OS-0030, filled 2026-11-02 and filed as AT 2020afkm (same ids, same option values)",
        candidate=lab, report_md=f"tns_report_{'OS-0035' if lab == 'M81_OS-0035' else 'NGC4945-obs3'}.md",
        select_rule="set selects by option value; dispatch input+change events (as done for OS-0030)",
        expected_select_display=EXPECT,
        remarks_length=len(remarks),
        fields=fields,
    )


def build_ngc4945(remarks):
    """Spitzer/IRAC discovery (coordinator decision 2026-11-03): one [3.6] discovery row ([4.5] did not cover the
    source in that AOR); last non-detection = the previous IRAC epoch (2017-10-03) in [3.6]."""
    lab = "NGC4945_obs3"
    n, s = N[lab], SPEC[lab]
    p = n["position"]
    d = n["discovery"]["phot"][0]
    nd36, nd45 = n["last_nondetection"]["phot"]
    meth = ("public post-BCD mosaic from IRSA; difference-aperture photometry (2.4\" radius, aperture-corrected) at the "
            "reported position against the median of 12 flat 2013-2016 epochs (leave-one-out)")
    nd_comment = (f"Instrument=Spitzer/IRAC (warm mission), [3.6], SPIRITS programme 13053 (PI M. Kasliwal), AOR "
                  f"{nd36['aor']}; {nd36['n_frames']} BCD frames at the source, {nd36['utc_first'][:16]} to "
                  f"{nd36['utc_last'][11:16]} UT; {meth}. Measured {nd36['uJy']:+.1f} +- {nd36['e_uJy']:.1f} uJy "
                  f"({nd36['snr']:.1f} sigma, below the 5-sigma threshold; the rise may already have begun). Limit is 5 "
                  f"sigma, AB. Same AOR [4.5]: {nd45['uJy']:+.1f} +- {nd45['e_uJy']:.1f} uJy ({nd45['snr']:.1f} sigma), "
                  f"5-sigma limit {nd45['lim5_AB']:.2f} AB.")
    p0 = (f"Instrument=Spitzer/IRAC (warm mission), [3.6], SPIRITS programme 13053 (PI M. Kasliwal), AOR {d['aor']}; "
          f"{d['n_frames']} BCD frames at the source, {d['utc_first'][:16]} to {d['utc_last'][11:16]} UT ([4.5] did not "
          f"cover the position in this AOR); {meth}. Difference flux {d['uJy']:.1f} +- {d['e_uJy']:.1f} uJy "
          f"({d['snr']:.1f} sigma). IRAC calibration/aperture systematic ~10%.")
    g = "edit-photometry-photometry-group-0-"
    fields = [
        dict(id="edit-ra-value", type="text", value=p["ra_hms"]),
        dict(id="edit-ra-error", type="text", value=f"{p['err_arcsec_quoted']}"),
        dict(id="edit-ra-units", type="select", value=SEL["arcsec"], label="arcsec"),
        dict(id="edit-decl-value", type="text", value=p["dec_dms"]),
        dict(id="edit-decl-error", type="text", value=f"{p['err_arcsec_quoted']}"),
        dict(id="edit-decl-units", type="select", value=SEL["arcsec"], label="arcsec"),
        dict(id="edit-reporting-groupid", type="select", value=SEL["None"], label="None"),
        dict(id="edit-data-source-groupid", type="select", value=SEL["None"], label="None"),
        dict(id="edit-reporter", type="text", value="Alan Shortz (Oddsky)"),
        dict(id="edit-discovery-datetime", type="text", value=d["utc_mid"]),
        dict(id="edit-at-type", type="select", value=SEL["Other - Undefined"], label="Other - Undefined"),
        dict(id="edit-host-name", type="text", value=s["host"]),
        dict(id="edit-host-redshift", type="text", value=s["z"]),
        dict(id="edit-internal-name", type="text", value=s["internal"]),
        dict(id="edit-remarks", type="text", value=remarks),
        dict(id="edit-non-detection-obsdate", type="text", value=nd36["utc_mid"]),
        dict(id="edit-non-detection-limiting-flux", type="text", value=f"{nd36['lim5_AB']:.2f}"),
        dict(id="edit-non-detection-flux-units", type="select", value=SEL["ABMag"], label="ABMag"),
        dict(id="edit-non-detection-filter-value", type="select", value=SEL["3.6-Spitzer IRAC"], label="3.6-Spitzer IRAC"),
        dict(id="edit-non-detection-instrument-value", type="select", value=SEL["SST - IRAC"], label="SST - IRAC"),
        dict(id="edit-non-detection-exptime", type="text", value=f"{nd36['exptime_s']:.1f}"),
        dict(id="edit-non-detection-observer", type="text", value=SP_OBS),
        dict(id="edit-non-detection-comments", type="text", value=nd_comment),
        dict(id=g + "obsdate", type="text", value=d["utc_mid"]),
        dict(id=g + "flux", type="text", value=f"{d['AB']:.2f}"),
        dict(id=g + "flux-error", type="text", value=f"{d['e_AB']:.2f}"),
        dict(id=g + "flux-units", type="select", value=SEL["ABMag"], label="ABMag"),
        dict(id=g + "filter-value", type="select", value=SEL["3.6-Spitzer IRAC"], label="3.6-Spitzer IRAC"),
        dict(id=g + "instrument-value", type="select", value=SEL["SST - IRAC"], label="SST - IRAC"),
        dict(id=g + "exptime", type="text", value=f"{d['exptime_s']:.1f}"),
        dict(id=g + "observer", type="text", value=SP_OBS),
        dict(id=g + "comments", type="text", value=p0),
        dict(id="edit-related-file-0", type="file", value=s["fig"]),
        dict(id="edit-related-files-related-files-group-0-related-file-comments", type="text", value=s["fig_comment"]),
    ]
    exp = dict(EXPECT)
    exp.update({"edit-non-detection-filter-value": "3.6-Spitzer IRAC [40] (mirror value; verify in the live list)",
                "edit-non-detection-instrument-value": "SST - IRAC [193] (mirror value; verify in the live list)",
                "edit-photometry-photometry-group-0-filter-value": "3.6-Spitzer IRAC [40] (verify)",
                "edit-photometry-photometry-group-0-instrument-value": "SST - IRAC [193] (verify)"})
    return dict(
        status="DRAFT - NOT SUBMITTED. Do not click #edit-submit without Alan's explicit go-ahead.",
        form_url="https://www.wis-tns.org/reports/at",
        precedent="OS-0030 form ids; discovery switched to Spitzer/IRAC per coordinator decision 2026-11-03",
        candidate=lab, report_md="tns_report_NGC4945-obs3.md",
        select_rule="set selects by option value; dispatch input+change events (as done for OS-0030). If 193/40 are "
                    "absent from the live lists, use instrument Other - Other [0] and filter Other with the band in comments.",
        expected_select_display=exp, expected_designation="AT 2018xxx (inferred: TNS names follow the discovery date)",
        remarks_length=len(remarks), fields=fields)


if __name__ == "__main__":
    REMARKS["NGC4945_obs3"] = REMARKS_NGC4945
    for lab in SPEC:
        f = build_ngc4945(REMARKS[lab]) if lab == "NGC4945_obs3" else build(lab, REMARKS[lab])
        name = "OS-0035" if lab == "M81_OS-0035" else "NGC4945-obs3"
        (PK / f"fill_{name}.json").write_text(json.dumps(f, indent=1, ensure_ascii=False))
        print(name, "remarks", len(REMARKS[lab]), "chars;", len(f["fields"]), "steps")
