"""Wide pairs: sense of projected rotation and its dipole. Development split unless --heldout."""
import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import handedness as hd  # noqa: E402

BINS = [(1e2, 1e3), (1e3, 1e4), (1e4, 3e4), (3e4, 1e5), (1e5, 2.1e5)]
COLS = ["source_id1", "source_id2", "ra1", "dec1", "ra2", "dec2", "parallax1", "parallax2", "parallax_error1", "parallax_error2",
        "pmra1", "pmra2", "pmdec1", "pmdec2", "pmra_error1", "pmra_error2", "pmdec_error1", "pmdec_error2",
        "phot_g_mean_mag1", "phot_g_mean_mag2", "ruwe1", "ruwe2", "bp_rp1", "bp_rp2",
        "pairdistance", "sep_AU", "binary_type", "R_chance_align"]


def unit(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    return np.column_stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])


def basis(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    e = np.column_stack([-np.sin(ra), np.cos(ra), np.zeros_like(ra)])
    n = np.column_stack([-np.sin(dec) * np.cos(ra), -np.sin(dec) * np.sin(ra), np.cos(dec)])
    return e, n


def rotation(d, naive=False):
    """z = (r x dv).n and its error, in rad mas/yr, from 3D vectors so that meridian convergence cannot leak in."""
    n1, n2 = unit(d.ra1.values, d.dec1.values), unit(d.ra2.values, d.dec2.values)
    e1, a1 = basis(d.ra1.values, d.dec1.values)
    e2, a2 = basis(d.ra2.values, d.dec2.values)
    mid = n1 + n2
    mid /= np.linalg.norm(mid, axis=1, keepdims=True)
    r = n2 - n1
    if naive:
        cd = np.cos(np.radians(0.5 * (d.dec1.values + d.dec2.values)))
        dra = (d.ra2.values - d.ra1.values + 180) % 360 - 180
        da, dd = np.radians(dra) * cd, np.radians(d.dec2.values - d.dec1.values)
        z = da * (d.pmdec2.values - d.pmdec1.values) - dd * (d.pmra2.values - d.pmra1.values)
    else:
        v1 = e1 * d.pmra1.values[:, None] + a1 * d.pmdec1.values[:, None]
        v2 = e2 * d.pmra2.values[:, None] + a2 * d.pmdec2.values[:, None]
        z = np.einsum("ij,ij->i", np.cross(r, v2 - v1), mid)
    # r x e . mid terms give the weight of each proper-motion component in z
    w = lambda basis_vec: np.einsum("ij,ij->i", np.cross(r, basis_vec), mid)
    var = (w(e1) * d.pmra_error1.values) ** 2 + (w(a1) * d.pmdec_error1.values) ** 2
    var += (w(e2) * d.pmra_error2.values) ** 2 + (w(a2) * d.pmdec_error2.values) ** 2
    return z, np.sqrt(var), hd.gal_vectors(*radec(mid))


def radec(xyz):
    return np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0])) % 360, np.degrees(np.arcsin(xyz[:, 2]))


def load(path, heldout, base_cuts=True):
    df = pd.read_parquet(path, columns=COLS)
    dev = hd.is_dev(df.source_id1.values)
    df = df[~dev if heldout else dev].copy()
    if base_cuts:
        df = df[(df.R_chance_align < 0.1) & (df.ruwe1 < 1.4) & (df.ruwe2 < 1.4) & (df.pairdistance * 3600 > 3)]
    return df


def select(df, naive=False):
    z, s, n = rotation(df, naive)
    keep = np.abs(z) > 3 * s
    out = df[keep].copy()
    out["y"] = np.sign(z[keep])
    out[["nx", "ny", "nz"]] = n[keep]
    return out


def fit(d):
    return hd.fit_dipole(d.y.values, d[["nx", "ny", "nz"]].values)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout", action="store_true")
    args = ap.parse_args()
    raw = load(f"{hd.RUNS}/data/elbadry/cat.parquet", args.heldout)
    print("split", "HELD-OUT" if args.heldout else "dev", "pairs after base cuts", len(raw))
    d = select(raw)
    print("with |z|/sig > 3:", len(d), " fraction", round(len(d) / len(raw), 3))
    print(hd.fmt("WB all", fit(d)))
    print(hd.fmt("WB all, naive tangent-plane z", fit(select(raw, naive=True))))
    for lo, hi in BINS:
        s = d[(d.sep_AU >= lo) & (d.sep_AU < hi)]
        if len(s) > 100:
            print(hd.fmt(f"s in [{lo:.0e},{hi:.1e}) au", fit(s)))
    print()
    print(hd.fmt("b>0", fit(d[d.nz > 0])))
    print(hd.fmt("b<0", fit(d[d.nz < 0])))
    near = d.parallax1 > d.parallax1.median()
    print(hd.fmt("near", fit(d[near])))
    print(hd.fmt("far", fit(d[~near])))
    gmax = d[["phot_g_mean_mag1", "phot_g_mean_mag2"]].max(axis=1)
    bright = gmax < gmax.median()
    print(hd.fmt("bright (fainter star < median)", fit(d[bright])))
    print(hd.fmt("faint", fit(d[~bright])))
    gmin = d[["phot_g_mean_mag1", "phot_g_mean_mag2"]].min(axis=1)
    clean = (gmin > 13) & ((d.phot_g_mean_mag1 - d.phot_g_mean_mag2).abs() < 1)
    print(hd.fmt("both G>13, |dG|<1", fit(d[clean])))
    print(hd.fmt("the rest", fit(d[~clean])))
    for ty in sorted(d.binary_type.astype(str).unique()):
        s = d[d.binary_type.astype(str) == ty]
        if len(s) > 500:
            print(hd.fmt(f"type {ty}", fit(s)))
