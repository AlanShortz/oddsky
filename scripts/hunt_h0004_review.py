"""Hunt H-0004, step 4b: one table a human can read. Joins scored.csv and vetted.csv, applies the
catalogue dispositions (a VSX Mira is a Mira), and writes hunts/H-0004/review.md plus review.csv.

  .venv/bin/python scripts/hunt_h0004_review.py [--scored scored.csv]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

here = Path("hunts/H-0004")

# VSX variability types and SIMBAD object types that settle the matter on their own
VSX_KNOWN = {
    "M": "Mira", "SR": "semiregular", "SRA": "semiregular", "SRB": "semiregular", "SRC": "semiregular", "SRD": "semiregular",
    "L": "irregular giant", "LB": "irregular giant", "LC": "irregular supergiant", "EA": "eclipsing", "EB": "eclipsing", "EW": "eclipsing",
    "YSO": "young star", "UXOR": "UX Ori young star", "INA": "young star", "INB": "young star", "INT": "young star", "IN": "young star",
    "CST": "constant", "DCEP": "Cepheid", "RVA": "RV Tau", "RVB": "RV Tau", "RV": "RV Tau", "NL": "nova-like", "UG": "dwarf nova",
    "RCB": "R CrB (already known)", "DYPER": "DY Per (already known)", "SDOR": "LBV", "ZAND": "symbiotic",
    "CEP": "Cepheid", "CWA": "W Vir (type II Cepheid)", "CWB": "BL Her (type II Cepheid)", "CW": "type II Cepheid", "RS": "RS CVn", "BY": "BY Dra",
    "UGZ": "dwarf nova", "UGSS": "dwarf nova", "ROT": "rotating variable", "ACV": "Ap variable", "ELL": "ellipsoidal", "VAR": "",
}
SIMBAD_KNOWN = {
    "Mi*": "Mira", "LP*": "long-period variable", "sr*": "semiregular", "Y*O": "young star", "TT*": "T Tauri", "Or*": "Orion variable",
    "EB*": "eclipsing", "RV*": "RV Tau", "Ce*": "Cepheid", "No*": "nova", "Sy*": "symbiotic", "RC*": "R CrB (already known)", "pA*": "post-AGB",
    "OH*": "OH/IR star", "BY*": "BY Dra", "Ro*": "rotating variable", "cC*": "Cepheid", "Pu*": "pulsating", "Be*": "Be star", "Em*": "emission-line star",
    "WV*": "W Vir (type II Cepheid)", "Y*?": "possible young star", "AB?": "possible AGB star", "AB*": "AGB star", "C*": "carbon star", "RR*": "RR Lyrae",
}


def disposition(row) -> str:
    vsx = str(row.get("vsx_names") or "")
    for m in re.finditer(r"\[([A-Z+:/|]+)\]", vsx):
        types = re.split(r"[+:/|]", m.group(1))
        for t in types:
            if t in VSX_KNOWN and VSX_KNOWN[t]:
                return f"known {VSX_KNOWN[t]} (VSX)"
    sim = str(row.get("simbad_2026") or "")
    m = re.search(r"\(([^,()]+), (\d+) refs\)", sim)
    if m and m.group(1).strip() in SIMBAD_KNOWN:
        label = SIMBAD_KNOWN[m.group(1).strip()]
        if label in ("carbon star", "possible AGB star", "AGB star", "possible young star"):
            return f"candidate, SIMBAD says {label}"
        return f"catalogued {label} (SIMBAD)"
    rc = row.get("rcb_catalogues")
    if isinstance(rc, str) and rc.strip():
        return "in an R CrB catalogue"
    w = row.get("w1_w2_median")
    notes = []
    if pd.notna(w) and w < 0.3:
        notes.append("no warm dust in WISE")
    if pd.notna(row.get("brightest_neighbour_flux_ratio")) and row["brightest_neighbour_flux_ratio"] >= 0.3:
        notes.append("bright neighbour")
    if pd.notna(row.get("abs_g")) and row.get("poe", 0) > 5 and row["abs_g"] > -1:
        notes.append(f"Gaia says M_G={row['abs_g']:.1f}: not a supergiant")
    return "candidate" + (" (" + "; ".join(notes) + ")" if notes else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", default="scored.csv")
    a = ap.parse_args()
    sc = pd.read_csv(here / a.scored)
    vt = pd.read_csv(here / "vetted.csv")
    df = sc.merge(vt.drop(columns=["verdict"]), on="id", how="inner")
    df["disposition"] = df.apply(disposition, axis=1)
    df = df.sort_values(["disposition", "depth"], ascending=[True, False])
    cols = ["id", "disposition", "verdict", "simbad_2026", "vsx_names", "gaia_g", "abs_g", "band", "depth", "decline_rate_mag_per_day",
            "asymmetry", "asymmetry_is_lower_bound", "n_events", "ongoing", "ls_power", "fold_power", "w1_w2_median", "w1_range",
            "brightest_neighbour_flux_ratio", "gaia_class", "ra", "dec", "glon", "glat", "k24_lc_pri", "k24_col_pri", "k24_class"]
    df[[c for c in cols if c in df]].to_csv(here / "review.csv", index=False)
    lines = ["# H-0004 picks under review", "", f"{len(df)} stars scored `rcb_like`/`eclipse_like`; dispositions from VSX, SIMBAD (2026), Gaia and NEOWISE.", ""]
    lines.append("| id | disposition | depth | rate /d | asym | events | ongoing | W1-W2 | G | M_G | SIMBAD | VSX |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        asym = "" if pd.isna(r.asymmetry) else f"{r.asymmetry:.1f}{'+' if r.asymmetry_is_lower_bound else ''}"
        lines.append(f"| {r.id} | {r.disposition} | {r.depth:.2f} | {r.decline_rate_mag_per_day:.2f} | {asym} | {int(r.n_events) if pd.notna(r.n_events) else ''} | "
                     f"{'yes' if r.ongoing else ''} | {'' if pd.isna(r.w1_w2_median) else f'{r.w1_w2_median:.2f}'} | {'' if pd.isna(r.gaia_g) else f'{r.gaia_g:.1f}'} | "
                     f"{'' if pd.isna(r.abs_g) else f'{r.abs_g:.1f}'} | {str(r.simbad_2026 or '')[:60]} | {str(r.vsx_names or '')[:40]} |")
    (here / "review.md").write_text("\n".join(lines) + "\n")
    print(df.disposition.str.split(" \\(").str[0].value_counts().to_string())
    print("\n".join(lines[4:]))


if __name__ == "__main__":
    main()
