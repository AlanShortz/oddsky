"""r6: data for the non-lens alternatives, for all 21 candidates.
  * Gaia DR3 astrophysical_parameters: GSP-Phot Teff/logg/A_G/distance, ESP-HS spectral type and Teff, ESP-ELS (emission-line
    star) class and pseudo-equivalent width of H-alpha, DSC class probabilities; gaia_source has_xp_continuous, parallax.
  * 2MASS PSC and AllWISE (IRSA TAP) nearest within 2": J-H, H-K, K-W1, W1-W2, W2-W3 for IR excess.
  * H-alpha photometry: VPHAS+ DR2 (II/341) and IPHAS DR2 (II/321) within 1.5" (VizieR, idia mirror then CDS): r-Halpha against
    the r-i of the unreddened main-sequence/giant locus is not attempted; the reddened-locus comparison uses the field stars
    within 60" (an emission-line star sits >= 0.1-0.2 mag above the field's r-Halpha vs r-i sequence).
Writes data/alternatives.csv. Run: uv run python -I hunts/H-0010/reviews/claude-referee-2026-11-01/r6_alternatives.py"""
import io, os, time
import numpy as np, pandas as pd, requests, pyvo

HERE = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(os.path.join(HERE, "data", "candidates21.csv"), dtype={"source_id": str})
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
p = os.path.join(HERE, "data", "gaia_ap.csv")
if not os.path.exists(p):
    tap = pyvo.dal.TAPService("https://gea.esac.esa.int/tap-server/tap")
    ids = ",".join(C.source_id)
    q = f"""SELECT a.source_id, a.teff_gspphot, a.logg_gspphot, a.ag_gspphot, a.ebpminrp_gspphot, a.distance_gspphot, a.mh_gspphot,
      a.spectraltype_esphs, a.teff_esphs, a.classlabel_espels, a.classlabel_espels_flag, a.classprob_espels_wcstar,
      a.classprob_espels_herbigstar, a.classprob_espels_ttauristar, a.classprob_espels_bestar, a.classprob_espels_pne, a.ew_espels_halpha,
      a.ew_espels_halpha_uncertainty, a.ew_espels_halpha_flag, a.ew_espels_halpha_model, a.classprob_dsc_combmod_star,
      a.classprob_dsc_combmod_whitedwarf, a.classprob_dsc_combmod_binarystar, a.evolstage_flame, a.radius_gspphot,
      s.has_xp_continuous, s.has_xp_sampled, s.parallax, s.parallax_error, s.phot_g_mean_mag, s.bp_rp
      FROM gaiadr3.astrophysical_parameters AS a JOIN gaiadr3.gaia_source AS s USING (source_id) WHERE source_id IN ({ids})"""
    tap.run_sync(q, timeout=600).to_table().to_pandas().to_csv(p, index=False)
A = pd.read_csv(p, dtype={"source_id": str}).set_index("source_id")


def irsa(q):
    for attempt in range(4):
        try:
            r = requests.post("https://irsa.ipac.caltech.edu/TAP/sync", data={"QUERY": q, "FORMAT": "csv"}, timeout=600)
            return pd.read_csv(io.StringIO(r.text))
        except Exception:  # noqa: BLE001
            time.sleep(20)
    return pd.DataFrame()


p2 = os.path.join(HERE, "data", "ir_phot.csv")
if not os.path.exists(p2):
    rows = []
    for c in C.itertuples():
        t = irsa(f"SELECT j_m,h_m,k_m,ph_qual,cc_flg, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{c.ra},{c.dec}))*3600 AS r FROM fp_psc "
                 f"WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{c.ra},{c.dec},{2/3600}))=1 ORDER BY r")
        w = irsa(f"SELECT w1mpro,w2mpro,w3mpro,w4mpro,ph_qual AS wq,cc_flags,nb, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{c.ra},{c.dec}))*3600 AS rw "
                 f"FROM allwise_p3as_psd WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{c.ra},{c.dec},{2/3600}))=1 ORDER BY rw")
        rec = {"name": c.name, "source_id": c.source_id}
        if len(t):
            rec.update(t.iloc[0].to_dict())
        if len(w):
            rec.update(w.iloc[0].to_dict())
        rows.append(rec)
        print(c.name, len(t), len(w), flush=True)
    pd.DataFrame(rows).to_csv(p2, index=False)
IR = pd.read_csv(p2, dtype={"source_id": str}).set_index("source_id")

VIZ = ["https://vizier.idia.ac.za/viz-bin/asu-tsv", "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"]


def viz(cat, ra, dec, r, cols):
    for base in VIZ:
        try:
            q = requests.get(base, params={"-source": cat, "-c": f"{ra} {dec}", "-c.rs": r, "-out": cols, "-out.add": "_r", "-out.max": 500},
                             timeout=150)
            if "#Name:" not in q.text and "#RESOURCE" not in q.text:
                continue
            lines = [ln for ln in q.text.splitlines() if ln and not ln.startswith("#")]
            if len(lines) < 3:
                return pd.DataFrame(), "ok-empty"
            return pd.read_csv(io.StringIO("\n".join([lines[0]] + lines[3:])), sep="\t"), "ok"
        except Exception:  # noqa: BLE001
            continue
    return None, "UNKNOWN"


p3 = os.path.join(HERE, "data", "halpha.csv")
if not os.path.exists(p3):
    rows = []
    for c in C.itertuples():
        rec = {"source_id": c.source_id, "name": c.name}
        for lab, cat, cols in (("vphas", "II/341/vphasp", "**"), ("iphas", "II/321/iphas2", "_r,r,i,ha,rmag,imag,hamag")):
            d, st = viz(cat, c.ra, c.dec, 60, "**")
            rec[f"{lab}_status"] = st
            if d is None or d.empty:
                continue
            d = d.apply(pd.to_numeric, errors="coerce")
            rcol = [k for k in d.columns if k.lower() in ("rmag2", "r2mag", "rmag", "r")]
            icol = [k for k in d.columns if k.lower() in ("imag", "i")]
            hcol = [k for k in d.columns if k.lower() in ("hamag", "ha", "halpha")]
            if not (rcol and icol and hcol):
                rec[f"{lab}_status"] = f"columns? {list(d.columns)[:25]}"
                continue
            d["ri"], d["rha"] = d[rcol[0]] - d[icol[0]], d[rcol[0]] - d[hcol[0]]
            d = d[np.isfinite(d.ri) & np.isfinite(d.rha)]
            me = d[d._r < 1.5].sort_values("_r")
            if me.empty:
                rec[f"{lab}_status"] += " (no source within 1.5\")"
                continue
            m = me.iloc[0]
            fld = d[(d._r > 3) & (np.abs(d.ri - m.ri) < 0.15)]
            rec.update({f"{lab}_r": m[rcol[0]], f"{lab}_ri": m.ri, f"{lab}_rha": m.rha, f"{lab}_field_rha_med": fld.rha.median(),
                        f"{lab}_field_rha_sig": 1.4826 * np.median(np.abs(fld.rha - fld.rha.median())) if len(fld) > 3 else np.nan,
                        f"{lab}_nfield": len(fld)})
        rows.append(rec)
        print(rec, flush=True)
        time.sleep(1)
    pd.DataFrame(rows).to_csv(p3, index=False)
H = pd.read_csv(p3, dtype={"source_id": str}).set_index("source_id")

out = []
for c in C.itertuples():
    a, ir, h = A.loc[c.source_id], IR.loc[c.source_id], H.loc[c.source_id]
    rec = dict(name=c.name, G=a.phot_g_mean_mag, bp_rp=a.bp_rp, plx=f"{a.parallax:.2f}+-{a.parallax_error:.2f}", teff_gspphot=a.teff_gspphot,
               ag=a.ag_gspphot, dist=a.distance_gspphot, esphs=a.spectraltype_esphs, teff_esphs=a.teff_esphs, espels=a.classlabel_espels,
               ew_halpha=a.ew_espels_halpha, ew_ha_err=a.ew_espels_halpha_uncertainty, xp=a.has_xp_continuous,
               JH=ir.get("j_m") - ir.get("h_m") if "j_m" in ir else np.nan, HK=ir.get("h_m") - ir.get("k_m") if "h_m" in ir else np.nan,
               KW1=ir.get("k_m") - ir.get("w1mpro") if "w1mpro" in ir else np.nan, W1W2=ir.get("w1mpro") - ir.get("w2mpro") if "w1mpro" in ir else np.nan,
               W2W3=ir.get("w2mpro") - ir.get("w3mpro") if "w3mpro" in ir else np.nan, wq=ir.get("wq"),
               vphas=f"r-Ha {h.get('vphas_rha'):.3f} vs field {h.get('vphas_field_rha_med'):.3f}+-{h.get('vphas_field_rha_sig'):.3f} (n {h.get('vphas_nfield')})" if np.isfinite(h.get("vphas_rha", np.nan)) else h.get("vphas_status"),
               iphas=f"r-Ha {h.get('iphas_rha'):.3f} vs field {h.get('iphas_field_rha_med'):.3f}+-{h.get('iphas_field_rha_sig'):.3f} (n {h.get('iphas_nfield')})" if np.isfinite(h.get("iphas_rha", np.nan)) else h.get("iphas_status"))
    out.append(rec)
O = pd.DataFrame(out)
O.to_csv(os.path.join(HERE, "data", "alternatives.csv"), index=False)
print(O.round(3).to_string(index=False))
