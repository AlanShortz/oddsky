"""Notebooks: each observer's working copy of the cases they investigate.

On first touch a casebook case is copied into the observer's workspace; every recording call
(claims, hypotheses, predictions, the ledger) then lands there and is mirrored to Cloud Storage, so
it survives instance restarts and is the same on every instance. Cases an observer opens on a new
star are named under their code (ASH-0001). `publish` snapshots a notebook to a public page.
"""

from __future__ import annotations

import os
import secrets
import shutil
import threading
from pathlib import Path

from ..case.store import CaseStore
from ..paths import workspace
from .db import db
from .ledger import now

CANON = Path(os.environ.get("ODDSKY_HOME", Path(__file__).resolve().parents[3])) / "cases"
WS_ROOT = Path(os.environ.get("ODDSKY_WORKSPACES", "/tmp/oddsky-ws"))
BUCKET = os.environ.get("ODDSKY_BUCKET")  # unset: notebooks live only on local disk (dev, tests)
PREFIX = "notebooks"
SMALL = ("case.yaml", "ledger.jsonl")
_locks: dict[str, threading.Lock] = {}
_gen: dict[str, int] = {}  # last Cloud Storage generation of ledger.jsonl we hold, per workspace case


def _lock(key: str) -> threading.Lock:
    return _locks.setdefault(key, threading.Lock())


def root(observer: str) -> Path:
    p = WS_ROOT / observer
    (p / "cases").mkdir(parents=True, exist_ok=True)
    return p


def _bucket():
    from google.cloud import storage

    return storage.Client().bucket(BUCKET)


def canon_id(ref: str) -> str | None:
    """A casebook case id for ref (id, path-less name or alias), or None."""
    with workspace(CANON.parent):
        try:
            return CaseStore.find(ref).path.name
        except FileNotFoundError:
            return None


def ensure(observer: str, ref: str) -> str:
    """Make sure case `ref` is in the observer's workspace and current; return its id."""
    ws = root(observer) / "cases"
    cid = ref.strip()
    local = ws / cid
    canon = canon_id(cid) if not (local / "case.yaml").exists() else None
    if canon:
        cid, local = canon, ws / canon
    with _lock(f"{observer}/{cid}"):
        remote_gen = _remote_generation(observer, cid)
        if (local / "case.yaml").exists() and (remote_gen is None or _gen.get(f"{observer}/{cid}") == remote_gen):
            return cid
        if not (local / "case.yaml").exists() and (CANON / cid / "case.yaml").exists():
            shutil.copytree(CANON / cid, local, dirs_exist_ok=True)
        if remote_gen is not None:
            _download(observer, cid, local, small_only=(CANON / cid).exists())
            _gen[f"{observer}/{cid}"] = remote_gen
        if not (local / "case.yaml").exists():
            raise FileNotFoundError(f"no case '{ref}' in the casebook or in your notebook; list_cases shows both")
    return cid


def _remote_generation(observer: str, cid: str) -> int | None:
    if not BUCKET:
        return None
    b = _bucket().get_blob(f"{PREFIX}/{observer}/{cid}/ledger.jsonl")
    return b.generation if b else None


def _download(observer: str, cid: str, local: Path, small_only: bool) -> None:
    pre = f"{PREFIX}/{observer}/{cid}/"
    for blob in _bucket().list_blobs(prefix=pre):
        rel = blob.name[len(pre):]
        if small_only and rel not in SMALL:
            continue
        dest = local / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(dest)


def sync(observer: str, cid: str, everything: bool = False) -> None:
    """Mirror the workspace copy of a case to Cloud Storage (just the argument and ledger, unless
    the case is the observer's own and its data is new)."""
    if not BUCKET:
        return
    local = root(observer) / "cases" / cid
    bucket = _bucket()
    files = [local / f for f in SMALL if (local / f).exists()]
    if everything or not (CANON / cid).exists():
        files = [p for p in local.rglob("*") if p.is_file()]
    gen = None
    for p in sorted(files, key=lambda p: p.name == "ledger.jsonl"):  # ledger last: its generation marks the sync
        blob = bucket.blob(f"{PREFIX}/{observer}/{cid}/{p.relative_to(local)}")
        blob.upload_from_filename(p)
        if p.name == "ledger.jsonl":
            gen = blob.generation
    if gen is not None:
        _gen[f"{observer}/{cid}"] = gen


def own_cases(observer: str) -> list[str]:
    """Cases in the observer's notebook: anything touched, plus their own new cases (from storage)."""
    out = {p.parent.name for p in (root(observer) / "cases").glob("*/case.yaml")}
    if BUCKET:
        for blob in _bucket().list_blobs(prefix=f"{PREFIX}/{observer}/", match_glob="**/case.yaml"):
            out.add(blob.name.split("/")[2])
    return sorted(out)


def publish(observer: str, cid: str, title: str, summary: str, agent: str | None) -> dict:
    s = CaseStore(root(observer) / "cases" / cid)
    c = s.load()
    nid = f"{cid.lower()}-{observer.lower()}-{secrets.token_hex(3)}"
    doc = {
        "id": nid, "observer": observer, "agent": agent, "case": cid, "title": title.strip()[:160],
        "summary": summary.strip()[:20000], "published_at": now(),
        "target": c.target.model_dump(mode="json") if c.target else None, "case_title": c.title,
        "claims": [x.model_dump(mode="json") for x in c.claims],
        "hypotheses": [x.model_dump(mode="json") for x in c.hypotheses],
        "predictions": [x.model_dump(mode="json") for x in c.predictions],
        "ledger": s.ledger()[-400:],
    }
    db().set("notebooks", nid, doc)
    return {"id": nid, "url": f"https://oddsky.ai/n/{nid}"}
