"""H-0012 target list: star-forming galaxies within 10 Mpc, and the unWISE tiles they need.

    uv run python hunts/H-0012/scripts/targets.py [--dmax 10] [--logsfr-min -2.5] [--amin 1.0]

Source: the Updated Nearby Galaxy Catalog (UNGC; Karachentsev, Makarov & Kaisina 2013, AJ 145, 101),
VizieR J/AJ/145/101/catalog, fetched as ASU-TSV from a VizieR mirror (vizier.idia.ac.za, falling back to
vizier.cfa.harvard.edu and CDS; CDS itself was timing out on 2026-11-01). The raw table is cached in
~/oddsky-runs/imaging/meta/ungc_J_AJ_145_101.tsv with the URL and date in a sidecar .json.

Star formation rate (Karachentsev & Kaisina 2013, AJ 146, 46, eqs. 1-2; D in Mpc):
    log SFR(FUV) = 2.78 - 0.4 m_FUV^c + 2 log D,   m_FUV^c = FUV - 1.93 A_B   (Galactic only)
    log SFR(Ha)  = 3.54 - 0.4 m_Ha^c  + 2 log D,   m_Ha^c  = Hamag - 0.538 A_B
(UNGC defines m_Ha = -2.5 log F(Ha) - 13.6 with F in erg/s/cm^2; with SFR = 7.9e-42 L(Ha), Kennicutt
1998, log SFR = log F + 2 log D + 8.98 = 3.54 - 0.4 m_Ha + 2 log D. Check: M33 gives log SFR(FUV) =
-0.5, LMC log SFR(Ha) = -0.6.)
Internal extinction is not corrected (SFRs are lower limits; the cut is conservative). Limits
(l_FUV / l_Hamag = '>') count as non-detections. A galaxy is star-forming if either SFR >= the cut.
UNGC has NO FUV or Ha flux for some of the biggest galaxies (M31, LMC, SMC) and for galaxies behind
the Milky Way plane; with no SFR measurement a galaxy is kept if it is a late type (T = 1-10,
Sa-Im) with M_B <= -14 (column sfr_basis = 'type').

Cuts: D <= dmax; log SFR >= logsfr_min (default -2.5, i.e. 0.003 Msun/yr); a26 >= amin arcmin
(galaxies smaller than ~1' are a few WISE PSFs across). The Milky Way satellites LMC and SMC are
listed but flagged 'separate project' (tens of tiles each). UNGC has no position angle, so the
search region per galaxy is a CIRCLE of diameter 1.2 x a26 (conservative: covers any PA).
Writes work/targets_10mpc.csv and work/targets_10mpc_summary.json.

v2 (2026-11-01, after the referee's triage report found M51's UNGC centre 141" off the nucleus):

- **Centres.** Every target's UNGC position is checked against NED (name resolution, preferred
  position) and the 2MASS Extended Source Catalog (IRSA fp_xsc: the brightest XSC source within 20" of
  the NED position, which is the near-IR light peak, i.e. where the nucleus mask must sit). Adopted
  centre: the hand-vetted oddsky.imaging.galaxies entry if there is one, else XSC, else NED, else UNGC.
  Columns ra/dec hold the adopted centre (ra_ungc/dec_ungc the original), with centre_source,
  centre_offset_arcsec (adopted - UNGC) and centre_corrected (offset > 10"). Tiles are recomputed from
  the adopted centre.
- **Bright sources** (work/bright_sources_10mpc.csv; oddsky.imaging.masks). The unWISE bitmask's
  bright-star footprints come from AllWISE w1mpro < 9.5 or w2mpro < 8.3 (Meisner et al. 2019, A1).
  For every target: those AllWISE sources within its search radius + 10' (the runner's window margin
  plus the 150-px bitmask padding). Each one with AllWISE ext_flg
  > 0, or within half the search radius of the centre, is checked against Gaia DR3 (2"). Galaxy light
  (is_star = False) = inside a26/2 AND no Gaia counterpart with parallax or proper motion > 5 sigma
  or G < 12.5.
  Everything else (Gaia stars, point-like sources far out, anything outside a26/2) is a star and stays
  masked. The runner releases the footprints of galaxy-light sources only.
- Caches: meta/ned_centres.json, meta/xsc_centres.csv, meta/allwise_bright.csv, meta/bright_gaia.csv.
"""

from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

from oddsky.data.http import request
from oddsky.imaging import crossmatch, fetch, tiles
from oddsky.imaging.galaxies import by_ungc_name

HERE = Path(__file__).resolve().parents[1]
MIRRORS = ("vizier.idia.ac.za", "vizier.cfa.harvard.edu", "vizier.cds.unistra.fr")
SEPARATE = {"LMC", "SMC"}


def fetch_ungc() -> tuple[pd.DataFrame, dict]:
    cache = fetch.cache_root() / "meta" / "ungc_J_AJ_145_101.tsv"
    side = cache.with_suffix(".json")
    if not cache.exists():
        last = None
        for host in MIRRORS:
            url = f"https://{host}/viz-bin/asu-tsv?-source=J/AJ/145/101/catalog&-out.max=unlimited&-out.all"
            try:
                text = request("GET", url, timeout=180, retries=2).text
                if "Name" in text:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_text(text)
                    side.write_text(json.dumps(dict(url=url, fetched=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))))
                    break
            except Exception as e:  # try the next mirror
                last = e
        else:
            raise RuntimeError(f"UNGC unavailable from all mirrors: {last}")
    lines = [ln for ln in cache.read_text().splitlines() if ln and not ln.startswith("#")]
    head = lines[0].split("\t")
    body = [ln for ln in lines[3:] if ln.split("\t")[0].strip().isdigit()]  # skip units/dashes rows
    df = pd.read_csv(io.StringIO("\n".join(["\t".join(head)] + body)), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].str.strip()
    num = ["a26", "b/a", "AB", "FUV", "Bmag", "Hamag", "Kmag", "TT", "Dist", "BMag", "KLum", "M26", "MHI"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, json.loads(side.read_text())


def sfr(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    logd = 2 * np.log10(df.Dist)
    fuv_ok = df.FUV.notna() & (df.l_FUV != ">")
    ha_ok = df.Hamag.notna() & (df.l_Hamag != ">")
    s_fuv = np.where(fuv_ok, 2.78 - 0.4 * (df.FUV - 1.93 * df.AB.fillna(0)) + logd, np.nan)
    s_ha = np.where(ha_ok, 3.54 - 0.4 * (df.Hamag - 0.538 * df.AB.fillna(0)) + logd, np.nan)
    return pd.Series(s_fuv, index=df.index), pd.Series(s_ha, index=df.index)


def _primary(ras, decs) -> list[str]:
    """Primary tile (nearest centre: unWISE's own de-duplication) of every point."""
    t = tiles.tile_table()
    tra, tdec = np.radians(np.asarray(t["ra"], float)), np.radians(np.asarray(t["dec"], float))
    tv = np.c_[np.cos(tdec) * np.cos(tra), np.cos(tdec) * np.sin(tra), np.sin(tdec)]
    ra, dec = np.radians(ras), np.radians(decs)
    pv = np.c_[np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)]
    ids = np.asarray(t["coadd_id"])
    return sorted({str(ids[np.argmax(tv @ v)]) for v in pv})


def tiles_for(ra: float, dec: float, diam_arcmin: float) -> list[str]:
    r = diam_arcmin / 2 / 60
    t = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    ras = np.r_[ra, ra + r * np.cos(t) / np.cos(np.radians(dec))]
    decs = np.r_[dec, dec + r * np.sin(t)]
    if r > 0.5:  # fill big discs too (tiles are 1.56 deg)
        g = np.arange(-r, r + 0.25, 0.25)
        gx, gy = np.meshgrid(g, g)
        inside = np.hypot(gx, gy) <= r
        ras = np.r_[ras, ra + gx[inside] / np.cos(np.radians(dec))]
        decs = np.r_[decs, dec + gy[inside]]
    return _primary(ras % 360, np.clip(decs, -90, 90))


# ----------------------------------------------------------------------------------------------
# v2: centres (NED, 2MASS XSC) and the unWISE bright-source list (AllWISE + Gaia)

IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
NED_LOOKUP = "https://ned.ipac.caltech.edu/srs/ObjectLookup"
CORRECT_ARCSEC = 10.0
XSC_MATCH_ARCSEC = 20.0


def sep_arcsec(ra1, dec1, ra2, dec2):
    ra1, dec1, ra2, dec2 = (np.radians(np.asarray(v, float)) for v in (ra1, dec1, ra2, dec2))
    s = np.sin((dec2 - dec1) / 2) ** 2 + np.cos(dec1) * np.cos(dec2) * np.sin((ra2 - ra1) / 2) ** 2
    return np.degrees(2 * np.arcsin(np.sqrt(np.clip(s, 0, 1)))) * 3600


def _name_variants(name: str, nedname: str | None) -> list[str]:
    import re

    out = [name]
    m = re.match(r"^([A-Za-z]+)\s*0*(\d.*)$", name)
    if m:
        out.append(f"{m.group(1)} {m.group(2)}")
    if nedname and nedname not in out:
        out.append(nedname)
    return out


def ned_centres(t: pd.DataFrame, nednames: dict | None = None, pace_s: float = 1.0) -> pd.DataFrame:
    """NED preferred position per target (name resolution; cached). Columns ned_ra, ned_dec, ned_name, ned_ref."""
    cache_p = fetch.cache_root() / "meta" / "ned_centres.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    for name in t.Name:
        if name in cache and cache[name].get("status") in ("ok", "unresolved"):
            continue
        rec = dict(status="unresolved")
        for v in _name_variants(name, (nednames or {}).get(name)):
            try:
                r = request("POST", NED_LOOKUP, timeout=60, retries=2, data={"json": json.dumps({"name": {"v": v}})})
                d = r.json()
            except Exception as e:  # noqa: BLE001
                rec = dict(status=f"ERR {type(e).__name__}")
                continue
            finally:
                time.sleep(pace_s)
            p = d.get("Preferred", {}) or {}
            pos = p.get("Position") or {}
            if d.get("ResultCode") == 3 and pos.get("RA") is not None:
                rec = dict(status="ok", query=v, ra=pos["RA"], dec=pos["Dec"], name=p.get("Name"), ref=pos.get("RefCode"),
                           type=(p.get("ObjType") or {}).get("Value"))
                break
        cache[name] = rec
        cache_p.parent.mkdir(parents=True, exist_ok=True)
        cache_p.write_text(json.dumps(cache, indent=1))
    rows = []
    for name in t.Name:
        c = cache.get(name, {})
        rows.append(dict(Name=name, ned_status=c.get("status", "not queried"), ned_ra=c.get("ra", np.nan),
                         ned_dec=c.get("dec", np.nan), ned_name=c.get("name", ""), ned_ref=c.get("ref", "")))
    return pd.DataFrame(rows).set_index("Name")


def _votable(rows: list[tuple]) -> bytes:
    body = "".join(f"<TR><TD>{k}</TD><TD>{a:.7f}</TD><TD>{d:.7f}</TD><TD>{r:.6f}</TD></TR>" for k, a, d, r in rows)
    return ('<?xml version="1.0"?><VOTABLE version="1.3" xmlns="http://www.ivoa.net/xml/VOTable/v1.3"><RESOURCE><TABLE>'
            '<FIELD name="cid" datatype="char" arraysize="*"/><FIELD name="ra" datatype="double"/>'
            '<FIELD name="dec" datatype="double"/><FIELD name="rdeg" datatype="double"/><DATA><TABLEDATA>' + body +
            "</TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>").encode()


def irsa_upload(query: str, rows: list[tuple]) -> pd.DataFrame:
    """IRSA TAP sync query against an uploaded table t(cid, ra, dec, rdeg)."""
    r = request("POST", IRSA_TAP, timeout=600, retries=3,
                data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query, UPLOAD="t,param:t"),
                files={"t": ("t.xml", _votable(rows), "application/x-votable+xml")})
    if r.text.lstrip().startswith("<"):
        raise RuntimeError(f"IRSA: {r.text[:300]}")
    return pd.read_csv(io.StringIO(r.text), dtype={"cid": str})


def xsc_centres(t: pd.DataFrame, ned: pd.DataFrame) -> pd.DataFrame:
    """Brightest (K_20fe) 2MASS XSC source within XSC_MATCH_ARCSEC of the NED position (UNGC if NED failed)."""
    cache_p = fetch.cache_root() / "meta" / "xsc_centres.csv"
    if cache_p.exists():
        x = pd.read_csv(cache_p, dtype={"cid": str})
    else:
        rows = []
        for r in t.itertuples():
            ra, dec = (ned.loc[r.Name, "ned_ra"], ned.loc[r.Name, "ned_dec"]) if np.isfinite(ned.loc[r.Name, "ned_ra"]) else (r.ra, r.dec)
            rows.append((r.Name, float(ra), float(dec), XSC_MATCH_ARCSEC / 3600))
        q = ("SELECT u.cid, x.designation, x.ra, x.dec, x.k_m_k20fe, x.r_k20fe FROM fp_xsc x, TAP_UPLOAD.t u "
             "WHERE CONTAINS(POINT('ICRS', x.ra, x.dec), CIRCLE('ICRS', u.ra, u.dec, u.rdeg)) = 1")
        x = irsa_upload(q, rows)
        x.to_csv(cache_p, index=False)
    x = x.sort_values(["cid", "k_m_k20fe"], na_position="last").drop_duplicates("cid")
    return x.rename(columns={"ra": "xsc_ra", "dec": "xsc_dec", "designation": "xsc_id", "k_m_k20fe": "xsc_k"}).set_index("cid")[
        ["xsc_ra", "xsc_dec", "xsc_id", "xsc_k"]]


def adopt_centres(t: pd.DataFrame, ned: pd.DataFrame, xsc: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["ra_ungc"], t["dec_ungc"] = t.ra, t.dec
    t = t.join(ned[["ned_status", "ned_ra", "ned_dec", "ned_name"]], on="Name").join(xsc, on="Name")
    src, ra_a, dec_a = [], [], []
    for r in t.itertuples():
        g = by_ungc_name(r.Name)
        ned_ok = r.ned_status == "ok" and np.isfinite(r.ned_ra) and sep_arcsec(r.ra, r.dec, r.ned_ra, r.ned_dec) < 600
        if g is not None:
            src.append(f"oddsky.imaging.galaxies ({g.name})")
            ra_a.append(g.ra), dec_a.append(g.dec)
        elif np.isfinite(r.xsc_ra) and (sep_arcsec(r.ned_ra, r.ned_dec, r.xsc_ra, r.xsc_dec) <= XSC_MATCH_ARCSEC if ned_ok
                                        else sep_arcsec(r.ra, r.dec, r.xsc_ra, r.xsc_dec) <= 60):
            # (an XSC source found round a NED position that is itself implausible, > 600" from UNGC, is not used)
            src.append(f"2MASS XSC {r.xsc_id}")
            ra_a.append(r.xsc_ra), dec_a.append(r.xsc_dec)
        elif ned_ok:
            src.append(f"NED ({r.ned_name})")
            ra_a.append(r.ned_ra), dec_a.append(r.ned_dec)
        elif r.ned_status == "ok":
            src.append(f"UNGC (NED '{r.ned_name}' > 600\" away: name conflict, not corrected)")
            ra_a.append(r.ra), dec_a.append(r.dec)
        else:
            src.append("UNGC (not verified)")
            ra_a.append(r.ra), dec_a.append(r.dec)
    t["ra_adopt"], t["dec_adopt"], t["centre_source"] = ra_a, dec_a, src
    t["centre_offset_arcsec"] = sep_arcsec(t.ra_ungc, t.dec_ungc, t.ra_adopt, t.dec_adopt)
    t["ned_offset_arcsec"] = sep_arcsec(t.ra_adopt, t.dec_adopt, t.ned_ra, t.ned_dec)
    t["xsc_offset_arcsec"] = sep_arcsec(t.ra_adopt, t.dec_adopt, t.xsc_ra, t.xsc_dec)
    t["centre_corrected"] = t.centre_offset_arcsec > CORRECT_ARCSEC
    t["ra"] = np.where(t.centre_corrected, t.ra_adopt, t.ra_ungc)
    t["dec"] = np.where(t.centre_corrected, t.dec_adopt, t.dec_ungc)
    return t


def bright_sources(t: pd.DataFrame, pad_arcmin: float = 10.0) -> pd.DataFrame:
    """The unWISE bright-source list (AllWISE w1mpro < 9.5 or w2mpro < 8.3) within each target's search
    radius + pad, with the Gaia verdict is_star (see the module docstring)."""
    cache_a = fetch.cache_root() / "meta" / "allwise_bright.csv"
    if cache_a.exists():
        a = pd.read_csv(cache_a, dtype={"cid": str})
    else:
        rows = [(r.Name, float(r.ra), float(r.dec), (r.search_diam_arcmin / 2 + pad_arcmin) / 60) for r in t.itertuples()]
        q = ("SELECT u.cid, a.designation, a.ra, a.dec, a.w1mpro, a.w2mpro, a.ext_flg, a.cc_flags FROM allwise_p3as_psd a, TAP_UPLOAD.t u "
             "WHERE CONTAINS(POINT('ICRS', a.ra, a.dec), CIRCLE('ICRS', u.ra, u.dec, u.rdeg)) = 1 AND (a.w1mpro < 9.5 OR a.w2mpro < 8.3)")
        a = pd.concat([irsa_upload(q, rows[i:i + 60]) for i in range(0, len(rows), 60)], ignore_index=True)
        a.to_csv(cache_a, index=False)
    a = a.rename(columns={"cid": "galaxy"})
    tg = t.set_index("Name")
    a["r_arcmin"] = sep_arcsec(a.ra, a.dec, tg.loc[a.galaxy, "ra"].to_numpy(), tg.loc[a.galaxy, "dec"].to_numpy()) / 60
    a["r_frac"] = a.r_arcmin / (tg.loc[a.galaxy, "search_diam_arcmin"].to_numpy() / 2)
    a["need_gaia"] = (a.ext_flg.fillna(0) > 0) | (a.r_frac <= 0.5)
    cache_g = fetch.cache_root() / "meta" / "bright_gaia.csv"
    g = pd.read_csv(cache_g, dtype={"designation": str, "gaia_id": str}) if cache_g.exists() else pd.DataFrame(columns=["designation"])
    todo = a[a.need_gaia & ~a.designation.isin(set(g.designation))].drop_duplicates("designation")
    for i in range(0, len(todo), 150):
        sub = todo.iloc[i:i + 150]
        gg = crossmatch.gaia_batch(sub.ra.to_numpy(), sub.dec.to_numpy(), r_arcsec=2.0)
        near = crossmatch.nearest(sub.assign(group=sub.designation), gg, r_arcsec=2.0).rename(columns={"group": "designation"})
        g = pd.concat([g, near], ignore_index=True)
        g.to_csv(cache_g, index=False)
        print(f"Gaia: {min(i + 150, len(todo))}/{len(todo)}", flush=True)
    g = g.drop_duplicates("designation", keep="last").set_index("designation")
    a = a.join(g[[c for c in ("gaia_id", "G", "plx_snr", "pm_snr", "foreground") if c in g]], on="designation")
    fg = a.get("foreground", pd.Series(False, index=a.index)).map(lambda v: str(v) == "True")
    # a Gaia counterpart brighter than G = 12.5 is a star even without a parallax solution (2-parameter
    # sources); the brightest galaxy core here in a 2" Gaia aperture is NGC 5102's at G = 14.2
    fg = fg | (pd.to_numeric(a.get("G", np.nan), errors="coerce") < 12.5)
    inside = a.r_arcmin <= tg.loc[a.galaxy, "a26"].to_numpy(float) / 2  # within the galaxy itself (a26/2)
    a["is_star"] = ~a.need_gaia | fg | ~inside
    a["verdict"] = np.where(~a.is_star, "galaxy light (inside a26/2, no Gaia star)",
                            np.where(fg, "star (Gaia plx/pm > 5 sigma or G < 12.5)",
                                     np.where(~inside, "star (outside a26/2; default)", "star (point-like; default)")))
    return a


def main(dmax=10.0, logsfr_min=-2.5, amin=1.0, scale=1.2):
    df, prov = fetch_ungc()
    c = SkyCoord(df.RAJ2000.values, df.DEJ2000.values, unit=(u.hourangle, u.deg))
    df["ra"], df["dec"] = c.ra.deg, c.dec.deg
    df["logSFR_FUV"], df["logSFR_Ha"] = sfr(df)
    df["logSFR"] = df[["logSFR_FUV", "logSFR_Ha"]].max(axis=1)
    by_type = df.logSFR.isna() & df.TT.between(1, 10) & (df.BMag <= -14)
    df["sfr_basis"] = np.where(df.logSFR.notna(), "FUV/Ha", np.where(by_type, "type", ""))
    sf = (df.logSFR >= logsfr_min) | by_type
    sel = (df.Dist <= dmax) & sf & (df.a26 >= amin) & (df.Name != "Milky Way")
    t = df[sel].copy()
    t["separate_project"] = t.Name.isin(SEPARATE)
    t["search_diam_arcmin"] = scale * t.a26
    # v2: verified centres (tiles follow the adopted centre)
    work = t[~t.separate_project]
    ned = ned_centres(work, nednames=dict(zip(df.Name, df.get("NEDname", df.Name), strict=True)))
    xsc = xsc_centres(work, ned)
    adopted = adopt_centres(work, ned, xsc)
    t = t.join(adopted[[c for c in adopted.columns if c not in t.columns]])
    t.loc[adopted.index, ["ra", "dec"]] = adopted[["ra", "dec"]].to_numpy()
    t["tiles"] = [",".join(tiles_for(r.ra, r.dec, r.search_diam_arcmin)) if not r.separate_project else ""
                  for r in t.itertuples()]
    t["n_tiles"] = [len(x.split(",")) if x else 0 for x in t.tiles]
    cols = ["Name", "ra", "dec", "Dist", "f_Dist", "a26", "b/a", "TT", "BMag", "logSFR_FUV", "logSFR_Ha", "logSFR", "sfr_basis",
            "search_diam_arcmin", "n_tiles", "tiles", "separate_project", "ra_ungc", "dec_ungc", "centre_source",
            "centre_offset_arcsec", "centre_corrected", "ned_name", "ned_offset_arcsec", "xsc_id", "xsc_offset_arcsec"]
    t = t[cols].sort_values("Dist").reset_index(drop=True)
    out = HERE / "work" / "targets_10mpc.csv"
    t.to_csv(out, index=False)
    bs = bright_sources(t[~t.separate_project.astype(bool)])
    bs_cols = ["galaxy", "designation", "ra", "dec", "w1mpro", "w2mpro", "ext_flg", "cc_flags", "r_arcmin", "r_frac", "gaia_id",
               "G", "plx_snr", "pm_snr", "is_star", "verdict"]
    bs[[c for c in bs_cols if c in bs]].to_csv(HERE / "work" / "bright_sources_10mpc.csv", index=False, float_format="%.6g")
    uniq = sorted({x for s in t.tiles for x in s.split(",") if x})
    summary = dict(
        source="UNGC, Karachentsev, Makarov & Kaisina 2013, AJ 145, 101 (VizieR J/AJ/145/101)", provenance=prov,
        n_ungc=int(len(df)), n_within_dmax=int((df.Dist <= dmax).sum()),
        n_sf_within_dmax=int(((df.Dist <= dmax) & sf & (df.Name != "Milky Way")).sum()),
        n_targets_sfr_from_type=int((t.sfr_basis == "type").sum()),
        n_targets=int(len(t)), n_separate_project=int(t.separate_project.sum()),
        n_unique_tiles=len(uniq),
        separate_project_tiles={r.Name: len(tiles_for(r.ra, r.dec, r.search_diam_arcmin)) for r in t[t.separate_project].itertuples()},
        cuts=dict(dmax_mpc=dmax, logsfr_min=logsfr_min, a26_min_arcmin=amin, search_scale=scale),
        n_by_distance={f"<{d}": int((t.Dist < d).sum()) for d in (1, 2, 4, 6, 8, 10.01)},
        largest=t.sort_values("n_tiles", ascending=False).head(8)[["Name", "Dist", "a26", "n_tiles"]].to_dict("records"),
        estimated_input_gb=round(len(uniq) * 1.0, 0),
        centres=dict(n_corrected=int(t.centre_corrected.fillna(False).astype(bool).sum()),
                     by_source=t.centre_source.fillna("").str.extract(r"^(\S+)")[0].value_counts().to_dict(),
                     corrected=t[t.centre_corrected.fillna(False).astype(bool)].sort_values("centre_offset_arcsec", ascending=False)[
                         ["Name", "centre_offset_arcsec", "centre_source"]].round(1).to_dict("records")),
        bright_sources=dict(n=int(len(bs)), n_galaxy_light=int((~bs.is_star.astype(bool)).sum()),
                            galaxies_with_released=int(bs[~bs.is_star.astype(bool)].galaxy.nunique())),
    )
    (HERE / "work" / "targets_10mpc_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dmax", type=float, default=10.0)
    ap.add_argument("--logsfr-min", type=float, default=-2.5)
    ap.add_argument("--amin", type=float, default=1.0)
    a = ap.parse_args()
    main(a.dmax, a.logsfr_min, a.amin)
