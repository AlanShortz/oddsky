"""Shared paths and loaders for the Gaia DR3 sweep of the H-0008/H-0009 strong events.
Run from the repo root:  uv run python -I hunts/H-0009/reviews/gaia-dr3-sweep-2026-10-31/sN_*.py"""
import os
import time

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
H9 = os.path.abspath(os.path.join(HERE, "..", ".."))
H8 = os.path.abspath(os.path.join(H9, "..", "H-0008"))
DATA = os.path.join(HERE, "data")
EPOCH = os.path.join(DATA, "epoch")
REF = os.path.join(H9, "reviews", "claude-referee-atlas-2026-10-31", "data")
UA = {"User-Agent": "Mozilla/5.0 (oddsky gaia-dr3 sweep)"}
DR3_T0, DR3_T1 = 56863.0, 57900.0  # Gaia DR3 epoch-photometry span (2014-07-25 .. 2017-05-28)
TAP = "https://gea.esac.esa.int/tap-server/tap/sync"


def mjd2date(t):
    return (pd.Timestamp("1858-11-17") + pd.to_timedelta(float(t), unit="D")).strftime("%Y-%m-%d")


def events():
    return pd.read_csv(os.path.join(DATA, "events.csv"), dtype={"g_source_id": str, "allwise_cntr": str})


def cones():
    return pd.read_csv(os.path.join(DATA, "cones.csv"), dtype={"source_id": str, "allwise_cntr": str})


def tap(query, tries=6, timeout=300):
    """ESA Gaia TAP (sync, ADQL, csv), retried with back-off; source_id columns come back as str."""
    last = None
    for k in range(tries):
        try:
            r = requests.post(TAP, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query), headers=UA, timeout=timeout)
            if r.status_code == 200 and not r.text.lstrip().startswith("<"):
                import io
                return pd.read_csv(io.StringIO(r.text), dtype={"source_id": str})
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(10 * (k + 1))
    raise RuntimeError(f"TAP failed after {tries} tries: {last}")
