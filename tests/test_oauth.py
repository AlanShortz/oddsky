"""An MCP client connects with no key: register, authorize (PKCE), approve on the website, exchange
the code, call /mcp. And without a token, /mcp answers 401 with the metadata pointer."""

import base64
import hashlib
import os
import secrets
import urllib.parse

import pytest

pytest.importorskip("webauthn")
os.environ.setdefault("ODDSKY_HOME", str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from starlette.testclient import TestClient  # noqa: E402

from oddsky.hosted import auth  # noqa: E402
from oddsky.hosted import db as dbmod  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(dbmod, "_db", dbmod.MemoryDB())
    from oddsky.hosted.app import create_app

    with TestClient(create_app(), base_url="https://oddsky.ai") as c:
        yield c


def test_mcp_client_signs_in_through_the_website(client):
    r = client.post("/register", json={"client_name": "Claude Code", "redirect_uris": ["http://localhost:33418/callback"],
                                       "grant_types": ["authorization_code"], "token_endpoint_auth_method": "none"})
    assert r.status_code == 201, r.text
    cid = r.json()["client_id"]
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    r = client.get("/authorize", params={"response_type": "code", "client_id": cid, "redirect_uri": "http://localhost:33418/callback",
                                         "code_challenge": challenge, "code_challenge_method": "S256", "state": "xyz"},
                   follow_redirects=False)
    assert r.status_code == 302 and "/observe?authorize=" in r.headers["location"]
    rid = r.headers["location"].split("authorize=")[1]
    assert client.get(f"/api/authorize/{rid}").json()["client_name"] == "Claude Code"

    dbmod.db().set("observers", "ASH", {"code": "ASH", "name": "Alan", "created_at": "now"})
    session = auth.new_session("ASH")
    r = client.post(f"/api/authorize/{rid}", json={"allow": True}, headers={"authorization": f"Bearer {session}"})
    back = urllib.parse.urlparse(r.json()["redirect"])
    q = urllib.parse.parse_qs(back.query)
    assert q["state"] == ["xyz"]
    r = client.post("/token", data={"grant_type": "authorization_code", "code": q["code"][0], "client_id": cid,
                                    "redirect_uri": "http://localhost:33418/callback", "code_verifier": verifier})
    assert r.status_code == 200, r.text
    tok = r.json()["access_token"]
    assert tok.startswith("osk_")
    assert auth.caller(f"Bearer {tok}")["observer"] == "ASH"

    h = {"authorization": f"Bearer {tok}", "accept": "application/json, text/event-stream"}
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=h)
    assert r.status_code == 200 and "case_overview" in r.text


def test_mcp_without_a_token_points_to_sign_in(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    headers={"accept": "application/json, text/event-stream"})
    assert r.status_code == 401
    assert "oauth-protected-resource" in r.headers.get("www-authenticate", "")
    meta = client.get("/.well-known/oauth-protected-resource/mcp").json()
    assert meta["resource"] == "https://oddsky.ai/mcp"
