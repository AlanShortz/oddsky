"""A polite Gaia archive client for release day.

The ESA archive is shared, and on 2026-11-02 it was already rejecting synchronous TAP jobs ("maximum number of synchronous
queued jobs (150) reached", HTTP 503). On DR4 day it will be busier. So this client:
  * spaces requests by `pause_s` and backs off exponentially on 429/5xx/timeouts (never on other 4xx: those are our bugs);
  * runs TAP queries as small async jobs (sync only for tiny lookups, and falls back to async if sync is refused);
  * records every failure as an error with its message. A failed request never turns into an empty result;
  * logs in if ~/.config/oddsky/gaia.env holds GAIA_USER and GAIA_PASSWORD (DataLink then takes 5,000 ids per request
    instead of 50). Without it, everything works anonymously.

Epoch photometry is parsed by `oddsky.data.gaia_epoch.to_series`, the function the sealed graders use, so a column fix
made there for DR4 applies to the pipeline too.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import httpx
import pandas as pd

from ..data import gaia_epoch
from ..data.http import UA
from .config import LOGIN, Release

log = logging.getLogger("oddsky.dr4day")

RETRY_STATUS = {429, 500, 502, 503, 504}
UWS_PHASES = {"PENDING", "QUEUED", "EXECUTING", "COMPLETED", "ERROR", "ABORTED", "UNKNOWN", "HELD", "SUSPENDED", "ARCHIVED"}


class ArchiveError(RuntimeError):
    pass


def _creds() -> tuple[str, str] | None:
    p = Path(os.environ.get("ODDSKY_GAIA_ENV", Path.home() / ".config" / "oddsky" / "gaia.env"))
    if not p.exists():
        return None
    kv = dict(line.split("=", 1) for line in p.read_text().splitlines() if "=" in line and not line.startswith("#"))
    u, pw = kv.get("GAIA_USER", "").strip(), kv.get("GAIA_PASSWORD", "").strip()
    return (u, pw) if u and pw else None


def _id_dtypes(text: str) -> dict:
    """Read every *source_id column as a string: 19-digit ids lose precision as float64."""
    head = text.split("\n", 1)[0]
    return {c: str for c in head.split(",") if c.strip().strip('"').endswith("source_id")}


class Archive:
    def __init__(self, rel: Release, *, retries: int = 4, backoff_s: float = 5.0, login: bool = True,
                 client: httpx.Client | None = None, sleep=time.sleep):
        self.rel = rel
        self.retries = retries
        self.backoff_s = backoff_s
        self.sleep = sleep
        self.client = client or httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=300)
        self._last = 0.0
        self.logged_in = False
        self.errors: list[dict] = []
        self.n_requests = 0
        if login and client is None and (c := _creds()):
            try:
                r = self._send("POST", LOGIN, data={"username": c[0], "password": c[1]}, tries=2)
                self.logged_in = r.status_code == 200
            except ArchiveError as e:
                self.error("login", str(e))

    @property
    def chunk(self) -> int:
        return self.rel.chunk_logged_in if self.logged_in else self.rel.chunk

    def error(self, where: str, message: str, **extra) -> dict:
        e = {"where": where, "error": message[:500], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **extra}
        self.errors.append(e)
        log.warning("%s: %s", where, message[:300])
        return e

    # ---- transport ------------------------------------------------------------------------------------------------
    def _send(self, method: str, url: str, tries: int | None = None, **kw) -> httpx.Response:
        last = None
        for attempt in range(tries or self.retries):
            wait = self.rel.pause_s - (time.monotonic() - self._last)
            if wait > 0:
                self.sleep(wait)
            self._last = time.monotonic()
            self.n_requests += 1
            try:
                r = self.client.request(method, url, **kw)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last = f"{type(e).__name__}: {e}"
            else:
                if r.status_code < 400:
                    return r
                msg = _service_message(r.text)
                last = f"HTTP {r.status_code}: {msg}"
                if r.status_code not in RETRY_STATUS or "No services found" in msg:
                    raise ArchiveError(last)  # our request is wrong, or the release/product is not served: retrying won't help
            self.sleep(self.backoff_s * 3 ** attempt)
        raise ArchiveError(f"{url} failed after {tries or self.retries} attempts: {last}")

    # ---- TAP -----------------------------------------------------------------------------------------------------
    def tap(self, query: str, *, sync: bool = False, max_wait_s: float = 3600) -> pd.DataFrame:
        """Run an ADQL query. Async by default (submit, poll with growing intervals, fetch); `sync=True` for tiny lookups,
        falling back to async if the server refuses the sync job."""
        params = dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=query)
        if sync:
            try:
                # two tries only: a busy sync queue (HTTP 503, seen 2026-11-02) is better met with an async job
                return _csv(self._send("POST", f"{self.rel.tap}/sync", data=params, tries=2).text)
            except ArchiveError as e:
                if "HTTP 4" in str(e) and "HTTP 429" not in str(e):
                    raise
                log.info("sync TAP refused (%s); trying async", str(e)[:120])
        r = self._send("POST", f"{self.rel.tap}/async", data={**params, "PHASE": "RUN"})
        job = str(r.url)
        t0, poll = time.monotonic(), 2.0
        while time.monotonic() - t0 < max_wait_s:
            phase = self._send("GET", f"{job}/phase").text.strip()
            if phase == "COMPLETED":
                return _csv(self._send("GET", f"{job}/results/result").text)
            if phase not in UWS_PHASES:
                raise ArchiveError(f"TAP job {job}: unexpected phase response {phase[:120]!r}")
            if phase in ("ERROR", "ABORTED"):
                raise ArchiveError(f"TAP job {phase}: {_job_message(self._send('GET', job).text)}")
            self.sleep(poll)
            poll = min(poll * 1.5, 30.0)
        raise ArchiveError(f"TAP job still running after {max_wait_s:.0f}s: {job}")

    def tap_in(self, template: str, ids: list[str], per: int = 500, **kw) -> pd.DataFrame:
        """`template` with `{ids}` replaced by comma-separated id chunks; results concatenated."""
        parts = []
        for i in range(0, len(ids), per):
            parts.append(self.tap(template.format(ids=",".join(ids[i:i + per])), **kw))
        parts = [p for p in parts if not p.empty]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    # ---- DataLink ------------------------------------------------------------------------------------------------
    def links(self, source_id: str) -> dict:
        """What DataLink offers for one source in this release: retrieval types, or the fault message."""
        r = self._send("GET", self.rel.links, params={"ID": f"{self.rel.name} {source_id}"})
        rows = _votable_rows(r.text)
        types = sorted({m.group(1) for row in rows if (m := re.search(r"RETRIEVAL_TYPE=([A-Z_]+)", row.get("access_url", "")))})
        faults = sorted({row["error_message"] for row in rows if row.get("error_message")})
        return {"retrieval_types": types, "faults": faults}

    def epoch_raw(self, ids: list[str]) -> list[pd.DataFrame]:
        """One DataLink EPOCH_PHOTOMETRY request; the raw per-source tables as served (no column mapping)."""
        r = self._send("POST", self.rel.datalink, data=dict(
            RETRIEVAL_TYPE=self.rel.retrieval_epoch, ID=",".join(str(i) for i in ids), FORMAT="csv",
            DATA_STRUCTURE=self.rel.data_structure, RELEASE=self.rel.name, VALID_DATA="false"))
        if not r.content:
            return []
        if not zipfile.is_zipfile(io.BytesIO(r.content)):
            raw = pd.read_csv(io.StringIO(r.text), comment="#", dtype={"source_id": str})
            if "source_id" not in raw:
                raise ArchiveError(f"epoch photometry response is not a table: {r.text[:200]!r}")
            return [g for _, g in raw.groupby("source_id")] if len(raw) else []
        out = []
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for name in z.namelist():
                raw = pd.read_csv(io.StringIO(z.read(name).decode()), comment="#", dtype={"source_id": str})
                if len(raw):
                    out.append(raw)
        return out

    def epoch_astrometry_raw(self, ids: list[str]) -> list[pd.DataFrame]:
        """One DataLink EPOCH_ASTROMETRY request (H-0015); the raw per-source tables as served. The per-CCD columns of
        DR4's draft data model are 10-element arrays; `oddsky.dr4day.astrometry.normalise` reads them."""
        r = self._send("POST", self.rel.datalink, data=dict(
            RETRIEVAL_TYPE=self.rel.retrieval_epoch_astrometry, ID=",".join(str(i) for i in ids), FORMAT="csv",
            DATA_STRUCTURE=self.rel.data_structure, RELEASE=self.rel.name, VALID_DATA="false"))
        if not r.content:
            return []
        texts = []
        if zipfile.is_zipfile(io.BytesIO(r.content)):
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                texts = [z.read(n).decode() for n in z.namelist()]
        else:
            texts = [r.text]
        out = []
        for txt in texts:
            raw = pd.read_csv(io.StringIO(txt), comment="#", dtype={"source_id": str})
            if "source_id" not in raw:
                raise ArchiveError(f"epoch astrometry response is not a table: {txt[:200]!r}")
            out += [g for _, g in raw.groupby("source_id")] if len(raw) else []
        return out

    def epoch(self, ids: list[str], cache: Path | None = None, on_chunk=None) -> tuple[dict[str, pd.DataFrame], list[dict]]:
        """Epoch photometry for many sources, chunked, cached per source, with one record per chunk.

        Returns (series by source_id, chunk records). A chunk that fails is retried with backoff and then recorded as an
        error (its ids are listed); it is never confused with sources that have no epoch photometry, which come back as
        status "absent" in the per-source table built by the caller."""
        out: dict[str, pd.DataFrame] = {}
        todo = []
        absent = set()
        if cache and (cache / "_absent.jsonl").exists():
            absent = {json.loads(x)["source_id"] for x in (cache / "_absent.jsonl").read_text().splitlines() if x.strip()}
        for s in ids:
            p = cache / f"{s}.csv" if cache else None
            if s in absent and not (p is not None and p.exists()):
                continue  # asked before and the release has no epoch photometry for it
            if p is not None and p.exists():
                out[s] = pd.read_csv(p, dtype={"camera": str})
            else:
                todo.append(s)
        recs = []
        for i in range(0, len(todo), self.chunk):
            part = todo[i:i + self.chunk]
            rec = {"chunk": i // self.chunk, "n_ids": len(part), "ok": False, "n_returned": 0, "error": ""}
            try:
                for raw in self.epoch_raw(part):
                    sid = str(raw.source_id.iloc[0])
                    df = gaia_epoch.to_series(raw)
                    out[sid] = df
                    if cache:
                        df.to_csv(cache / f"{sid}.csv", index=False)
                    rec["n_returned"] += 1
                rec["ok"] = True
                if cache:  # remember who was asked and came back empty, so a re-run does not ask again
                    got = {p.stem for p in cache.glob("*.csv")}
                    with open(cache / "_absent.jsonl", "a") as f:
                        for s in part:
                            if s not in got:
                                f.write(json.dumps({"source_id": s}) + "\n")
            except Exception as e:  # noqa: BLE001  recorded, not swallowed: the ids of a failed chunk are listed
                rec["error"] = f"{type(e).__name__}: {str(e)[:300]}"
                rec["ids"] = part
                self.error("epoch_photometry", rec["error"], n_ids=len(part))
            recs.append(rec)
            if on_chunk:
                on_chunk(rec)
        return out, recs


def _csv(text: str) -> pd.DataFrame:
    text = text.strip()
    if not text:
        return pd.DataFrame()
    if text.lstrip().startswith("<"):
        raise ArchiveError(f"expected CSV, got markup: {_service_message(text)}")
    return pd.read_csv(io.StringIO(text), dtype=_id_dtypes(text))


def _service_message(text: str) -> str:
    m = re.search(r"<b>Message: </b>(.*?)</li>", text or "", re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:300]
    m = re.search(r'<INFO name="QUERY_STATUS" value="ERROR"[^>]*>(.*?)</INFO>', text or "", re.S)
    if m:
        return re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip()[:300]
    return re.sub(r"<[^>]+>|\s+", " ", text or "").strip()[:300]


def _job_message(text: str) -> str:
    try:
        return "".join(e.text or "" for e in ET.fromstring(text).iter() if e.tag.endswith("message"))[:300] or text[:300]
    except ET.ParseError:
        return text[:300]


def _votable_rows(text: str) -> list[dict]:
    root = ET.fromstring(text)
    ns = {"v": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {}
    q = (lambda t: f"v:{t}") if ns else (lambda t: t)
    fields = [f.get("name") for f in root.iter(f"{{{ns['v']}}}FIELD" if ns else "FIELD")]
    rows = []
    for tr in root.iter(f"{{{ns['v']}}}TR" if ns else "TR"):
        vals = [(td.text or "").strip() for td in tr.findall(q("TD"), ns)]
        rows.append(dict(zip(fields, vals, strict=False)))
    return rows
