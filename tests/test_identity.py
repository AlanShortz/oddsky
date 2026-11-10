"""Sign-in with GitHub/Google: new people claim a code, returning people are signed in, linking adds a method,
and an identity already linked to one observer can't be linked to another."""

import urllib.parse

import pytest

pytest.importorskip("webauthn")

from oddsky.hosted import auth, identity  # noqa: E402
from oddsky.hosted import db as dbmod  # noqa: E402


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setattr(dbmod, "_db", dbmod.MemoryDB())
    monkeypatch.setenv("ODDSKY_GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("ODDSKY_GITHUB_CLIENT_SECRET", "secret")
    monkeypatch.setattr(identity, "_profile", lambda p, code: {"uid": code, "handle": f"user{code}", "name": "Alan Shortz"})


def _state(url):
    return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["state"][0]


def test_new_person_claims_a_code_then_signs_straight_in():
    assert identity.enabled() == [{"id": "github", "label": "GitHub"}]
    to = identity.callback("github", "42", _state(identity.start("github", "/observe?authorize=abc")))
    assert to.startswith("/observe?claim=")
    token = urllib.parse.parse_qs(urllib.parse.urlparse(to).query)["claim"][0]
    info = identity.claim_info(token)
    assert info["suggestions"][0] == "ASH"
    r = identity.claim(token, "ash", None)
    assert r["observer"]["code"] == "ASH" and r["next"] == "/observe?authorize=abc"
    assert auth.caller(f"Bearer {r['token']}")["observer"] == "ASH"
    again = identity.callback("github", "42", _state(identity.start("github", "/observe")))
    assert again.startswith("/observe#session=oss_")


def test_linking_and_no_hijack():
    dbmod.db().set("observers", "SG", {"code": "SG", "name": "Sam", "created_at": "x"})
    to = identity.callback("github", "7", _state(identity.link_intent("github", "SG", "/observe")))
    assert to.endswith("#linked=github")
    assert [x["provider"] for x in identity.linked("SG")] == ["github"]
    dbmod.db().set("observers", "XYZ", {"code": "XYZ", "name": "", "created_at": "x"})
    to = identity.callback("github", "7", _state(identity.link_intent("github", "XYZ", "/observe")))
    assert "signin_error" in to and "SG" in urllib.parse.unquote(to)


def test_bad_state_is_refused():
    assert "signin_error=expired" in identity.callback("github", "1", "forged")
