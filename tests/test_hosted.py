"""The hosted service's pure parts: the hash chain, sealing and grading, the scoreboard, workspaces."""

import json

import pytest

pytest.importorskip("webauthn")

from oddsky.hosted import db as dbmod  # noqa: E402
from oddsky.hosted import sky  # noqa: E402
from oddsky.hosted.ledger import GENESIS, verify  # noqa: E402


@pytest.fixture(autouse=True)
def memdb(monkeypatch):
    monkeypatch.setattr(dbmod, "_db", dbmod.MemoryDB())
    sky._cache.clear()


def _pred(p=0.8, pid="P1"):
    return {"id": pid, "statement": "s", "probability": p,
            "check": {"series": "AAVSO:V", "start": 61000.0, "end": 61100.0, "statistic": "median", "op": "<", "value": 0.1}}


def test_chain_verifies_and_detects_tampering():
    a = sky.seal(observer="ASH", agent="t", model="m", case="OS-0001", target="x", prediction=_pred())
    b = sky.seal(observer="ASH", agent="t", model="m", case="OS-0001", target="x", prediction=_pred(pid="P2"))
    rows = dbmod.db().log_range()
    assert a["prev"] == GENESIS and b["prev"] == a["hash"]
    assert verify(rows)["ok"]
    body = json.loads(rows[0]["body"])
    body["probability"] = 0.99
    rows[0] = {**rows[0], "body": json.dumps(body)}
    assert not verify(rows)["ok"]


def test_grades_feed_the_scoreboard():
    a = sky.seal(observer="ASH", agent=None, model="m1", case="C", target=None, prediction=_pred(0.9))
    b = sky.seal(observer="ASH", agent=None, model="m1", case="C", target=None, prediction=_pred(0.2, "P2"))
    sky.grade_entry(a, "true")
    sky.grade_entry(b, "true")
    d = sky.docket()
    row = d["board"]["observers"][0]
    assert row["graded"] == 2 and row["true"] == 2
    assert row["brier"] == pytest.approx(((0.9 - 1) ** 2 + (0.2 - 1) ** 2) / 2)
    assert not dbmod.db().all("pending")


def test_workspace_case_ids_use_the_observer_code(tmp_path):
    from oddsky.case.store import CaseStore
    from oddsky.paths import workspace

    (tmp_path / "cases" / "ASH-0001").mkdir(parents=True)
    with workspace(tmp_path, case_prefix="ASH"):
        assert CaseStore.next_case_id() == "ASH-0002"


def test_git_import_is_idempotent():
    import os

    os.environ.setdefault("ODDSKY_ADMIN_TOKEN", "t")
    from starlette.testclient import TestClient

    from oddsky.hosted import app as appmod

    appmod.ADMIN = "t"
    item = {"case": "OS-0015", "target": "x", "model": "m", "at": "2026-10-27T00:00:00+00:00",
            "prediction": {"id": "P1", "statement": "s", "probability": 0.7, "check": None, "resolve_by": "2028-01-01"}}
    with TestClient(appmod.create_app(), base_url="https://oddsky.ai") as c:
        h = {"x-oddsky-admin": "t"}
        assert c.post("/api/admin/genesis", json={"items": [item]}, headers=h).json()["sealed"] == [1]
        r = c.post("/api/admin/genesis", json={"items": [item, {**item, "prediction": {**item["prediction"], "id": "P2"}}]}, headers=h).json()
        assert r["skipped"] == 1 and r["sealed"] == [2]
