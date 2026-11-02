"""H-0012 v2 mask census: masked search area and masked W1 light per galaxy, v1 rule (h0012a: every unWISE
artefact bit, the runner's UNGC centre and nucleus radius) against v2 (oddsky.imaging.masks: galaxy-core
"bright star" footprints released and flagged low-confidence, saturated cores kept, verified centres,
acceptance-test nucleus radii and companion masks).

    uv run python hunts/H-0012/scripts/mask_census_v2.py [GALAXY ...]

Per galaxy: the tile holding its centre, the galaxy's window on it, the full-depth bitmask and ONE neo11 W1
epoch image as the reference proxy (what is cached; the referee's mask_light.py used the same). Area =
fraction of the search circle; light = fraction of the sky-subtracted W1 light in it. Saturated cores come
from coverage (n-m < 2 exposures in more than half the cached epochs; one epoch where only one is cached). The v1 numbers use
the h0012a target row (work/targets_10mpc.csv as of commit 871a846, saved by the v2 run in
~/oddsky-runs/imaging/scratch/v2/targets_10mpc_v1.csv); v2 uses the current target list and
bright_sources_10mpc.csv. Writes work/mask_census_v2.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "infra" / "gcp"))
from imaging_tile import galaxy_from_row  # noqa: E402

from oddsky.imaging import fetch, tiles  # noqa: E402
from oddsky.imaging.galaxies import Galaxy  # noqa: E402
from oddsky.imaging.pipeline import Config, build_mask_set, window_for  # noqa: E402
from oddsky.imaging.stack import window_wcs  # noqa: E402

DEFAULT = ["MESSIER082", "NGC4736", "NGC5102", "MESSIER081", "NGC0253", "NGC4945", "NGC5194"]
V1_TARGETS = Path("~/oddsky-runs/imaging/scratch/v2/targets_10mpc_v1.csv").expanduser()


class _St:  # the attributes build_mask_set reads
    def __init__(self, tile, band, window, wcs):
        self.tile, self.band, self.window, self.wcs = tile, band, window, wcs


def v1_galaxy(r) -> Galaxy:
    """h0012a's galaxy_from_row: UNGC centre, nucleus 4% of a26 (10-150"), no companion masks."""
    nuc = float(min(150.0, max(10.0, 0.04 * r["a26"] * 60)))
    return Galaxy(str(r["Name"]), float(r["ra"]), float(r["dec"]), float(r["a26"]), 1.0, 0.0, float(r["Dist"]),
                  nucleus_mask_arcsec=nuc, search_scale=1.2)


def epoch_image(tile: str):
    for ep in (13, 12, 14, 11, 15, 10, 16, 0):
        p = fetch.local_path(tile, 1, ep, "img-m")
        if p.exists():
            return fits.getdata(p).astype(np.float32), ep
    raise FileNotFoundError(f"no cached W1 epoch for {tile}")


def valid_fraction(tile: str, window, ep: int) -> np.ndarray:
    """Fraction of W1 epochs with >= 2 exposures per pixel (saturated cores lose exposures): every cached
    epoch's n-m; if only one epoch image is cached, that epoch's n-m (fetched if missing, ~4 MB)."""
    y0, y1, x0, x1 = window
    eps = [e for e in fetch.list_epochs(tile) if fetch.local_path(tile, 1, e, "n-m").exists()] \
        if (fetch.cache_root() / "meta" / f"epochs_{tile}.json").exists() else []
    if not eps:
        p = fetch.local_path(tile, 1, ep, "n-m")
        fetch.download(f"{fetch.BASE}/{fetch.rel_path(tile, 1, ep, 'n-m')}", p)
        eps = [ep]
    v = np.zeros((y1 - y0, x1 - x0))
    for e in eps:
        v += fits.getdata(fetch.local_path(tile, 1, e, "n-m"))[y0:y1, x0:x1] >= 2
    return v / len(eps)


def census(name: str, t_v1: pd.DataFrame, t_v2: pd.DataFrame, bright: pd.DataFrame) -> dict:
    r1, r2 = t_v1.loc[name], t_v2.loc[name]
    g2 = galaxy_from_row(r2, t_v2.reset_index(drop=True), bright)
    g1 = v1_galaxy(r1)
    best = None
    for t in str(r2.tiles).split(","):
        x, y = tiles.wcs_for(t).all_world2pix([[g2.ra, g2.dec]], 0)[0]
        e = min(x, y, 2047 - x, 2047 - y)
        if best is None or e > best[0]:
            try:
                epoch_image(t)
            except FileNotFoundError:
                continue
            best = (e, t)
    tile = best[1]
    img, ep = epoch_image(tile)
    out = dict(galaxy=name, tile=tile, epoch=ep, centre_v1=f"{g1.ra:.5f} {g1.dec:+.5f}", centre_v2=f"{g2.ra:.5f} {g2.dec:+.5f}",
               centre_shift_arcsec=float(np.hypot((g2.ra - g1.ra) * np.cos(np.radians(g2.dec)), g2.dec - g1.dec) * 3600),
               nucleus_v1=g1.nucleus_mask_arcsec, nucleus_v2=g2.nucleus_mask_arcsec, n_bright_sources=len(g2.bright_sources))
    for tag, gal, release in (("v1", g1, False), ("v2", g2, True)):
        cfg = Config(release_galaxy_cores=release)
        win = window_for(gal, tile, cfg.margin)
        y0, y1, x0, x1 = win
        ref = img[y0:y1, x0:x1]
        st = _St(tile, 1, win, window_wcs(tiles.wcs_for(tile), y0, x0))
        vf = valid_fraction(tile, win, ep)
        ms = build_mask_set(st, gal, cfg, ref, np.where(np.isfinite(ref) & (vf > 0), 1.0, np.nan), valid_frac=vf)
        c = ms.census(ref)
        out[f"area_masked_{tag}"] = c["masked_v2"]  # with release off, 'v2' == the v1 rule
        out[f"light_masked_{tag}"] = c["light_masked_v2"]
        if tag == "v2":
            out.update(area_lowconf_v2=c["released_lowconf"], light_lowconf_v2=c["light_lowconf"], area_saturated_v2=c["saturated"],
                       area_star_kept_v2=c["star_kept"], n_released_sources=c["n_released_sources"],
                       released=";".join(f"{d['ra']:.4f}{d['dec']:+.4f}" for d in c["released"]))
    return out


def main(names):
    t_v1 = pd.read_csv(V1_TARGETS).set_index("Name", drop=False)
    t_v2 = pd.read_csv(HERE / "work" / "targets_10mpc.csv").set_index("Name", drop=False)
    bright = pd.read_csv(HERE / "work" / "bright_sources_10mpc.csv")
    rows = [census(n, t_v1, t_v2, bright) for n in names]
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "work" / "mask_census_v2.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    print(df[["galaxy", "tile", "centre_shift_arcsec", "nucleus_v1", "nucleus_v2", "area_masked_v1", "area_masked_v2",
              "light_masked_v1", "light_masked_v2", "area_lowconf_v2", "light_lowconf_v2", "area_saturated_v2",
              "n_released_sources"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
