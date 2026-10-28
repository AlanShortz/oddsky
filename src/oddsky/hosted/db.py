"""Storage for the hosted service: Firestore in production, a dict in tests and local dev.

Collections: observers/{code}, credentials/{credential id}, challenges/{id}, sessions/{token sha},
keys/{key sha}, notebooks/{id}, log/{seq:09d} with the chain head in meta/head.
"""

from __future__ import annotations

import os
import threading
from typing import Any

from .ledger import GENESIS, make_entry


class MemoryDB:
    def __init__(self):
        self.data: dict[str, dict[str, dict]] = {}
        self.lock = threading.Lock()

    def get(self, coll: str, id: str) -> dict | None:
        d = self.data.get(coll, {}).get(id)
        return dict(d) if d else None

    def set(self, coll: str, id: str, doc: dict) -> None:
        self.data.setdefault(coll, {})[id] = dict(doc)

    def update(self, coll: str, id: str, fields: dict) -> None:
        self.data.setdefault(coll, {}).setdefault(id, {}).update(fields)

    def delete(self, coll: str, id: str) -> None:
        self.data.get(coll, {}).pop(id, None)

    def where(self, coll: str, field: str, value: Any, limit: int = 500) -> list[dict]:
        rows = [dict(d, _id=k) for k, d in self.data.get(coll, {}).items() if d.get(field) == value]
        return rows[:limit]

    def all(self, coll: str, limit: int = 500) -> list[dict]:
        return [dict(d, _id=k) for k, d in list(self.data.get(coll, {}).items())[:limit]]

    def append_log(self, content: dict) -> dict:
        with self.lock:
            head = self.get("meta", "head") or {"seq": 0, "hash": GENESIS}
            e = make_entry(head["seq"] + 1, head["hash"], content)
            self.set("log", f"{e['seq']:09d}", e)
            self.set("meta", "head", {"seq": e["seq"], "hash": e["hash"]})
            return e

    def log_range(self, after: int = 0, limit: int = 1000) -> list[dict]:
        rows = sorted(self.data.get("log", {}).values(), key=lambda e: e["seq"])
        return [e for e in rows if e["seq"] > after][:limit]

    def head(self) -> dict:
        return self.get("meta", "head") or {"seq": 0, "hash": GENESIS}


class FirestoreDB:
    def __init__(self, project: str | None = None):
        from google.cloud import firestore

        self.fs = firestore
        self.c = firestore.Client(project=project)

    def get(self, coll, id):
        s = self.c.collection(coll).document(id).get()
        return s.to_dict() if s.exists else None

    def set(self, coll, id, doc):
        self.c.collection(coll).document(id).set(doc)

    def update(self, coll, id, fields):
        self.c.collection(coll).document(id).set(fields, merge=True)

    def delete(self, coll, id):
        self.c.collection(coll).document(id).delete()

    def where(self, coll, field, value, limit=500):
        from google.cloud.firestore_v1.base_query import FieldFilter

        q = self.c.collection(coll).where(filter=FieldFilter(field, "==", value)).limit(limit)
        return [dict(s.to_dict(), _id=s.id) for s in q.stream()]

    def all(self, coll, limit=500):
        return [dict(s.to_dict(), _id=s.id) for s in self.c.collection(coll).limit(limit).stream()]

    def append_log(self, content: dict) -> dict:
        head_ref = self.c.collection("meta").document("head")
        tx = self.c.transaction()

        @self.fs.transactional
        def go(tx):
            snap = head_ref.get(transaction=tx)
            head = snap.to_dict() if snap.exists else {"seq": 0, "hash": GENESIS}
            e = make_entry(head["seq"] + 1, head["hash"], content)
            tx.set(self.c.collection("log").document(f"{e['seq']:09d}"), e)
            tx.set(head_ref, {"seq": e["seq"], "hash": e["hash"]})
            return e

        return go(tx)

    def log_range(self, after=0, limit=1000):
        q = (self.c.collection("log").order_by("seq").where(filter=self._gt("seq", after)).limit(limit))
        return [s.to_dict() for s in q.stream()]

    def _gt(self, field, value):
        from google.cloud.firestore_v1.base_query import FieldFilter

        return FieldFilter(field, ">", value)

    def head(self):
        return self.get("meta", "head") or {"seq": 0, "hash": GENESIS}


_db = None


def db():
    global _db
    if _db is None:
        _db = FirestoreDB(os.environ.get("GOOGLE_CLOUD_PROJECT")) if os.environ.get("ODDSKY_DB", "memory") == "firestore" else MemoryDB()
    return _db
