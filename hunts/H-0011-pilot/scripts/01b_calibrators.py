"""H-0011 pilot, step 1b: calibration stars with known behaviour, resolved in SIMBAD (Harvard mirror).

WOH G64 (RSG -> yellow hypergiant, 2013.5-2014.5; Munoz-Sanchez+2024), dusty/OH-maser RSGs and super-AGB candidates
(IRAS 05280-6910, IRAS 05346-6949, IRAS 05402-6956, IRAS 05558-7000, HV 888, HV 5870, HV 12501, HV 11417, HV 2112),
LMC LBVs and B[e]/post-RSG stars (S Dor, R71, R110, R127, HD 269582, LHA 120-S 61, IRAS 04530-6916, HD 269953,
HD 269723, IRAS 05298-6957).

Writes work/sample_cal.csv (same columns as sample_mc.csv where available).
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("s1", HERE / "01_sample.py")
s1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1)

NAMES = {
    "WOH G 64": "RSG->YHG transition 2013.5-2014.5 (Munoz-Sanchez+2024)",
    "IRAS 05280-6910": "dusty OH/IR RSG in NGC 1984",
    "IRAS 05346-6949": "dusty RSG/OH-IR",
    "IRAS 05402-6956": "OH/IR star (Mira-like)",
    "IRAS 05558-7000": "OH/IR star (Mira-like)",
    "HV 888": "luminous M4Ia RSG",
    "HV 5870": "M3.5Iae RSG",
    "HV 12501": "LPV RSG",
    "HV 11417": "SMC RSG, TZO candidate",
    "HV 2112": "SMC TZO/super-AGB candidate",
    "WOH G 17": "LMC LPV",
    "S Dor": "LBV",
    "HD 269006": "R71, LBV (outburst 2005-2012+)",
    "HD 269662": "R110, LBV",
    "HD 269858": "R127, LBV",
    "HD 269582": "LBV candidate (MWC 112)",
    "LHA 120-S 61": "WN11h / LBV candidate",
    "IRAS 04530-6916": "B[e] supergiant, dusty",
    "HD 269953": "post-RSG yellow supergiant (B[e]-like dust)",
    "HD 269723": "yellow supergiant",
    "IRAS 05298-6957": "post-AGB/dusty",
}


def main():
    lst = ",".join("'" + n + "'" for n in NAMES)
    d = s1.tap(f"""SELECT i.id AS query_id, b.oid, b.main_id, b.ra, b.dec, b.otype, b.sp_type, b.plx_value
                   FROM ident i JOIN basic b ON b.oid = i.oidref WHERE i.id IN ({lst})""")
    # SIMBAD ident keeps double spaces in some names: match on the normalised form
    norm = {" ".join(k.split()): v for k, v in NAMES.items()}
    d["note"] = d.query_id.map(lambda s: norm.get(" ".join(s.replace("SV* ", "").replace("V* ", "").split()), ""))
    d = d.merge(s1.fluxes_and_ids(d.oid.tolist()), on="oid", how="left")
    d["galaxy"] = ""
    for gal, (ra0, de0, rad) in s1.CENTRE.items():
        d.loc[s1.sep_deg(d.ra, d.dec, ra0, de0) < rad, "galaxy"] = gal
    d["J_K"] = d["J"] - d["K"]
    d["M_K"] = d["K"] - d.galaxy.map(s1.MU)
    d["logL"] = (4.74 - (d["M_K"] + s1.BC_K)) / 2.5
    missing = set(norm) - {" ".join(s.replace("SV* ", "").replace("V* ", "").split()) for s in d.query_id}
    print("unresolved:", missing)
    d.to_csv(s1.WORK / "sample_cal.csv", index=False)
    print(d[["main_id", "otype", "sp_type", "K", "J_K", "logL", "note"]].to_string())


if __name__ == "__main__":
    main()
