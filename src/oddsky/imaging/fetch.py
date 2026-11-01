"""Download unWISE time-resolved (epochal) coadds into a disk cache outside the repo.

Source: the neo11 epochal coadds Aaron Meisner serves from NERSC (2010-2024, e000..eNNN per tile;
e000 is the first WISE pass over the tile, Jan/Jul 2010). The directory is unofficial ("temp") but
public; the official unWISE pages only carry full-depth coadds and the unTimely catalogs. Override
with $ODDSKY_UNWISE_EPOCHS if it moves.

Layout, both remote and cached:  <base>/eNNN/<ra3>/<tile>/unwise-<tile>-w<b>-<kind>.fits[.gz]

Kinds: img-m (the outlier-rejected coadd, Vega nanomaggies, ZP 22.5), invvar-m (inverse
variance of img-m, excludes source Poisson noise), n-m (number of exposures per pixel).
~20 MB per tile, band and epoch for these three.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import logging
import os
import sys
from pathlib import Path

import httpx

from ..data.http import UA

log = logging.getLogger("oddsky")

BASE = os.environ.get(
    "ODDSKY_UNWISE_EPOCHS", "https://portal.nersc.gov/project/cosmo/temp/ameisner/neo11"
)
KINDS = ("img-m", "invvar-m", "n-m")
_SUFFIX = {"img-m": ".fits", "img-u": ".fits", "frames": ".fits"}


FULLDEPTH = "https://portal.nersc.gov/project/cosmo/data/unwise/neo11/unwise-coadds/fulldepth"
# unWISE bitmask (Meisner et al. 2019, PASP 131, 124504, Table 2): bits that mark DIFFERENCE-image
# artefacts (bright-star cores and saturation, scan-direction ghosts, latents, diffraction spikes).
# Not masked: 6 (pixel centre not primary: tile overlap), 9 (resolved galaxy), 10 (big object:
# M31/LMC/SMC), and 23-24 (AllWISE-like circular halos). Halos flag static, smooth light that biases
# catalogue fluxes but subtracts out in a difference image; masking them blinded 11% of NGC 6946's
# search area (0.8% of M31's), including N6946-BH1. (Halos were masked until 2026-11-01; dropping
# them was prompted by finding BH1 masked, and is disclosed as such in hunts/H-0012/README.md.)
NOT_ARTIFACT = (6, 9, 10, 23, 24)
ARTIFACT_BITS = sum(1 << b for b in range(31) if b not in NOT_ARTIFACT)


def cache_root() -> Path:
    p = Path(os.environ.get("ODDSKY_IMAGING_CACHE", "~/oddsky-runs/imaging")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def epochs_dir() -> Path:
    return cache_root() / "cache" / "unwise-neo11"


def filename(coadd_id: str, band: int, kind: str) -> str:
    return f"unwise-{coadd_id}-w{band}-{kind}{_SUFFIX.get(kind, '.fits.gz')}"


def rel_path(coadd_id: str, band: int, epoch: int, kind: str) -> str:
    return f"e{epoch:03d}/{coadd_id[:3]}/{coadd_id}/{filename(coadd_id, band, kind)}"


def local_path(coadd_id: str, band: int, epoch: int, kind: str) -> Path:
    return epochs_dir() / rel_path(coadd_id, band, epoch, kind)


def _client() -> httpx.Client:
    return httpx.Client(timeout=300, headers={"User-Agent": UA}, follow_redirects=True)


def download(url: str, dest: Path, client: httpx.Client | None = None, retries: int = 3) -> Path:
    """Stream url to dest atomically (dest.part then rename). Skips files already present."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.{os.getpid()}.part")  # unique per process: parallel fetches never collide
    own = client is None
    client = client or _client()
    try:
        for attempt in range(retries):
            try:
                with client.stream("GET", url) as r:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_bytes(1 << 20):
                            f.write(chunk)
                tmp.rename(dest)
                return dest
            except (httpx.HTTPError, OSError) as e:
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                    raise FileNotFoundError(url) from e
                log.warning("download %s failed (%s), attempt %d", url, e, attempt + 1)
        raise RuntimeError(f"{url}: gave up after {retries} attempts")
    finally:
        if own:
            client.close()


def list_epochs(coadd_id: str, max_gap: int = 3, max_epoch: int = 500) -> list[int]:
    """Epoch numbers available for a tile (cached). Probes eNNN/<ra3>/<tile>/ until max_gap misses."""
    meta = cache_root() / "meta" / f"epochs_{coadd_id}.json"
    if meta.exists():
        return json.loads(meta.read_text())
    found, miss = [], 0
    with _client() as c:
        for e in range(max_epoch):
            r = c.get(f"{BASE}/e{e:03d}/{coadd_id[:3]}/{coadd_id}/")
            if r.status_code == 200 and filename(coadd_id, 1, "img-m") in r.text:
                found.append(e)
                miss = 0
            else:
                miss += 1
                if miss >= max_gap and found:
                    break
                if miss >= 30 and not found:
                    break
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(found))
    return found


def fetch_tile(coadd_id: str, bands=(1, 2), epochs: list[int] | None = None, kinds=KINDS,
               workers: int = 3) -> list[Path]:
    """Download every (band, epoch, kind) file of a tile; returns local paths (skips cached)."""
    epochs = list_epochs(coadd_id) if epochs is None else epochs
    jobs = [(b, e, k) for e in epochs for b in bands for k in kinds]
    out: list[Path] = []
    with _client() as c, cf.ThreadPoolExecutor(workers) as ex:
        futs = {
            ex.submit(download, f"{BASE}/{rel_path(coadd_id, b, e, k)}", local_path(coadd_id, b, e, k), c): (b, e, k)
            for b, e, k in jobs
        }
        for f in cf.as_completed(futs):
            try:
                out.append(f.result())
            except FileNotFoundError as err:
                log.warning("missing: %s", err)
    return out


def fetch_mask(coadd_id: str) -> Path:
    """The full-depth unWISE bitmask of a tile (bright-star cores, saturation, ghosts, latents,
    halos, diffraction spikes), shared by every epoch."""
    name = f"unwise-{coadd_id}-msk.fits.gz"
    return download(f"{FULLDEPTH}/{coadd_id[:3]}/{coadd_id}/{name}",
                    cache_root() / "cache" / "unwise-fulldepth" / name)


if __name__ == "__main__":  # python -m oddsky.imaging.fetch TILE [TILE ...]
    logging.basicConfig(level=logging.INFO)
    for tile in sys.argv[1:]:
        eps = list_epochs(tile)
        print(tile, "epochs", eps, flush=True)
        paths = fetch_tile(tile, epochs=eps)
        fetch_mask(tile)
        print(tile, len(paths), "files", flush=True)
