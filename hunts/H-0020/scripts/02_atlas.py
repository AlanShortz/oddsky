"""AGB atlas, version 0: one row per red star within 2 mag above or 0.5 mag below the red-giant tip that the Hubble
Source Catalog saw at least twice in ACS/WFC F814W, in every galaxy of hunts/H-0019 (M31 excluded: its tip was misplaced
and its download predates the paging fix). Each row carries what was measured, how it changed, and what the catalogue's
photometry is worth for a star like it (hunts/H-0020 quality card: completeness, offset, scatter, gross-error rate by
position relative to the tip and by crowding).

Writes atlas/agb_atlas_v0.parquet, atlas/agb_atlas_v0_sample.csv and atlas/galaxies.csv.
"""
import glob, json, pathlib
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from oddsky.analysis import twiceseen

RUN = pathlib.Path.home() / "oddsky-runs/h0019"; HERE = pathlib.Path(__file__).resolve().parents[1]; H19 = HERE.parent / "H-0019"
meas = pd.read_csv(H19 / "work/measure.csv").set_index("name")
card = pd.read_csv(HERE / "work/hsc_quality.csv"); card = card[card.hsc.str.startswith("point-like") & card.crowding.isin(["isolated", "crowded"])]   # atlas stars passed the same CI cut
pooled = card.groupby(["range", "crowding"]).apply(lambda g: pd.Series({c: np.average(g[c], weights=g.n) for c in ("completeness", "offset", "scatter", "gross")}), include_groups=False)
own = card.groupby(["galaxy", "range", "crowding"]).apply(lambda g: pd.Series({c: np.average(g[c], weights=g.n) for c in ("completeness", "offset", "scatter", "gross")}), include_groups=False)
off = json.loads((H19 / "work/rediscovery_m33.json").read_text())["offset_arcsec"]
yuan = pd.DataFrame([dict(id=q[0], ra=float(q[1]), dec=float(q[2]), per=float(q[3]), amp=float(q[5])) for q in
                     ([x.strip() for x in ln.split("\t")] for ln in (RUN / "cat/m33_yuan2017.tsv").read_text().splitlines() if not ln.startswith("#"))
                     if len(q) >= 7 and q[0][:2].isdigit()])
lib = pd.read_csv(H19 / "work/candidates_librarian.csv")[["MatchID", "verdict"]].drop_duplicates("MatchID")
rows, gal_rows = [], []
for f in sorted(glob.glob(str(H19 / "work/pairs/*.parquet"))):
    key = pathlib.Path(f).stem
    name = key.replace("_", " ") if key.replace("_", " ") in meas.index else key
    if key == "MESSIER031" or name not in meas.index or not (RUN / f"hsc/{key}_sum.parquet").exists():
        continue
    m = meas.loc[name]
    p = pd.read_parquet(f); p = p[p.box.isin(["agb", "agb_bright", "rgb"])]
    if not len(p):
        continue
    # local scatter of the control stars in the same image pair, by magnitude
    p["sigma_local"] = np.nan
    for _, idx in p.groupby(["kind", "img1", "img2"]).indices.items():
        q = p.iloc[idx]; c = (q.box == "rgb").values
        if c.sum() >= 30:
            p.iloc[idx, p.columns.get_loc("sigma_local")] = max(1.4826 * float(np.median(np.abs(q.d.values[c]))), 0.015)
    long, short = p[p.kind == "long"].set_index("MatchID"), p[p.kind == "short"].set_index("MatchID")
    ids = long.index.union(short.index)
    base = p.drop_duplicates("MatchID").set_index("MatchID").loc[ids]
    out = pd.DataFrame({"galaxy": name, "MatchID": ids, "ra": base.MatchRA.values, "dec": base.MatchDec.values, "f814w_ab_aper": base.A_F814W.values,
                        "colour": base.col.values, "colour_band": str(m.colour), "mag_above_tip": -base.rel.values, "box": base.box.values, "n_visits": base.NumVisits.values,
                        "lag_days": long.lag.reindex(ids).values, "change_long": long.d.reindex(ids).values, "change_short": short.d.reindex(ids).values,
                        "sigma_local": long.sigma_local.reindex(ids).fillna(short.sigma_local.reindex(ids)).values})
    out["z_long"] = out.change_long / out.sigma_local
    # crowding from the catalogue itself: neighbours within 0.5" no more than 1 mag fainter
    s = pd.read_parquet(RUN / f"hsc/{key}_sum.parquet", columns=["MatchID", "MatchRA", "MatchDec", "A_F814W"]).dropna()
    ra0, dec0 = float(s.MatchRA.median()), float(s.MatchDec.median())
    sxy = twiceseen.plane(s.MatchRA, s.MatchDec, ra0, dec0); tree = cKDTree(sxy); smag = s.A_F814W.values
    oxy = twiceseen.plane(out.ra, out.dec, ra0, dec0)
    out["crowd"] = [int((smag[js] < mg + 1.0).sum()) - 1 for js, mg in zip(tree.query_ball_point(oxy, 0.5), out.f814w_ab_aper.values, strict=True)]
    rng_ = np.where(out.mag_above_tip >= 0, "above tip", "0-1 below tip"); cls = np.where(out.crowd > 0, "crowded", "isolated")
    src = "this galaxy" if key in own.index.get_level_values(0) else "pooled over five galaxies"
    for c in ("completeness", "offset", "scatter", "gross"):
        out["q_" + c] = [float(own.loc[(key, r, k), c]) if (key, r, k) in own.index else float(pooled.loc[(r, k), c]) for r, k in zip(rng_, cls, strict=True)]
    out["q_source"] = src
    out["known_variable"] = ""; out["known_period_d"] = np.nan
    if key == "MESSIER033":
        cd = np.cos(np.radians(dec0)); yt = cKDTree(np.c_[(yuan.ra + off[0] / 3600 / cd) * cd * 3600, (yuan.dec + off[1] / 3600) * 3600])
        d, j = yt.query(np.c_[out.ra * cd * 3600, out.dec * 3600], distance_upper_bound=0.15); ok = np.isfinite(d)
        out.loc[ok, "known_variable"] = "Yuan+2017 " + yuan.id.values[j[ok]]; out.loc[ok, "known_period_d"] = yuan.per.values[j[ok]]
    out = out.merge(lib.rename(columns={"verdict": "librarian"}), on="MatchID", how="left")
    measured = bool(m.tip_sig >= 4)                       # else the tip is the prediction from the catalogue distance
    soft = bool(measured and abs(m.tip - m.tip_pred) > 0.2)   # a measured edge far from the prediction (H-0019: M33, IC 10)
    out["tip_source"] = "edge" if measured else "predicted"; out["tip_soft"] = soft
    rows.append(out)
    gal_rows.append(dict(galaxy=name, dist_mpc=m.dist, tip_ab_aper=m.tip, tip_predicted=m.tip_pred, tip_source="edge" if measured else "predicted", tip_soft=soft, colour_band=m.colour, n_stars=len(out),
                         n_above_tip=int((out.mag_above_tip >= 0).sum()), n_with_long_pair=int(out.lag_days.notna().sum()), quality_from=src))
A = pd.concat(rows, ignore_index=True)
for c in A.select_dtypes("float64"):
    A[c] = A[c].astype("float32") if c not in ("ra", "dec") else A[c]
A.to_parquet(HERE / "atlas/agb_atlas_v0.parquet", index=False)
A.sort_values("z_long", key=lambda v: -v.abs()).head(200).round(5).to_csv(HERE / "atlas/agb_atlas_v0_sample.csv", index=False)
G = pd.DataFrame(gal_rows).sort_values("dist_mpc"); G.to_csv(HERE / "atlas/galaxies.csv", index=False)
print(len(A), "stars in", A.galaxy.nunique(), "galaxies;", int(A.lag_days.notna().sum()), "with a long pair;", int((A.known_variable != "").sum()), "known variables")
print(A.groupby(["box"]).size().to_dict(), "| crowded share", round(float((A.crowd > 0).mean()), 3), "| tip soft galaxies:", G[G.tip_soft].galaxy.tolist())
print(G.to_string(index=False))
