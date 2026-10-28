"""The Sky Ledger: an append-only, hash-chained log.

Each entry stores its content as a canonical JSON string (`body`) and

    hash = sha256( prev_hash + "\\n" + body )

so a verifier never has to reproduce our JSON serialisation, only hash the stored string. The first
entry's prev_hash is GENESIS. Entry kinds:

- "seal":  a prediction (observer, model, case, statement, probability, machine-checkable check, resolve_by)
- "grade": the sky's answer to an earlier seal (ref = its seq and hash, outcome, observed value, note)
- "note":  anything else worth recording (e.g. "imported from git")
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

GENESIS = "0" * 64


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def chain_hash(prev: str, body: str) -> str:
    return hashlib.sha256(f"{prev}\n{body}".encode()).hexdigest()


def make_entry(seq: int, prev: str, content: dict) -> dict:
    body = canonical({"seq": seq, **content})
    return {"seq": seq, "prev": prev, "body": body, "hash": chain_hash(prev, body)}


def verify(entries: list[dict]) -> dict:
    """Re-hash a run of entries (in seq order). Returns {ok, checked, first_bad}."""
    prev = None
    for e in entries:
        if prev is not None and e["prev"] != prev:
            return {"ok": False, "checked": e["seq"], "first_bad": e["seq"], "why": "prev does not match the previous hash"}
        if chain_hash(e["prev"], e["body"]) != e["hash"]:
            return {"ok": False, "checked": e["seq"], "first_bad": e["seq"], "why": "hash does not match body"}
        if json.loads(e["body"]).get("seq") != e["seq"]:
            return {"ok": False, "checked": e["seq"], "first_bad": e["seq"], "why": "seq in body differs"}
        prev = e["hash"]
    return {"ok": True, "checked": len(entries), "first_bad": None}


def content(entry: dict) -> dict:
    return json.loads(entry["body"])
