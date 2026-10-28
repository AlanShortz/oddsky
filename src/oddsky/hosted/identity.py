"""Sign in with GitHub or Google.

The observer code is the identity; GitHub, Google and passkeys are ways to prove you hold it. An
observer can link several, which is also how they recover the account if they lose a device.

Flow: /api/oauth/<provider>/start → the provider → /api/oauth/<provider>/callback, which either signs
the person in (identity already linked), links it to the signed-in observer, or, for someone new, sends
them to /observe?claim=<token> to choose an observer code. Session tokens travel back in the URL
fragment, which browsers never send to a server.

Configured by ODDSKY_GITHUB_CLIENT_ID/_SECRET and ODDSKY_GOOGLE_CLIENT_ID/_SECRET; a provider without
credentials is simply not offered.
"""

from __future__ import annotations

import os
import re
import secrets
import time
import urllib.parse

import httpx

from . import auth
from .db import db
from .ledger import now

SITE = os.environ.get("ODDSKY_SITE", "https://oddsky.ai")

PROVIDERS = {
    "github": {
        "authorize": "https://github.com/login/oauth/authorize",
        "token": "https://github.com/login/oauth/access_token",
        "scope": "read:user",
        "label": "GitHub",
    },
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "openid email profile",
        "label": "Google",
    },
}


def creds(p: str) -> tuple[str, str] | None:
    cid, sec = os.environ.get(f"ODDSKY_{p.upper()}_CLIENT_ID"), os.environ.get(f"ODDSKY_{p.upper()}_CLIENT_SECRET")
    return (cid, sec) if cid and sec else None


def enabled() -> list[dict]:
    return [{"id": p, "label": v["label"]} for p, v in PROVIDERS.items() if creds(p)]


def _redirect_uri(p: str) -> str:
    return f"{SITE}/api/oauth/{p}/callback"


def _safe_next(nxt: str | None) -> str:
    return nxt if nxt and nxt.startswith("/") and not nxt.startswith("//") else "/observe"


def start(p: str, nxt: str | None, link_observer: str | None = None) -> str:
    if p not in PROVIDERS or not creds(p):
        raise ValueError(f"sign-in with {p} is not available")
    state = secrets.token_urlsafe(24)
    db().set("challenges", f"oauth-{state}", {"kind": "oauth", "provider": p, "next": _safe_next(nxt),
                                              "link": link_observer, "expires": time.time() + 600})
    q = {"client_id": creds(p)[0], "redirect_uri": _redirect_uri(p), "scope": PROVIDERS[p]["scope"], "state": state}
    if p == "google":
        q |= {"response_type": "code", "prompt": "select_account"}
    else:
        q |= {"allow_signup": "true"}
    return f"{PROVIDERS[p]['authorize']}?{urllib.parse.urlencode(q)}"


def link_intent(p: str, observer: str, nxt: str | None) -> str:
    """A signed-in observer linking another provider: the browser navigates, so it can't carry the
    session header; we mint the state server-side and hand back the provider URL."""
    return start(p, nxt or "/observe", link_observer=observer)


def _profile(p: str, code: str) -> dict:
    cid, sec = creds(p)
    with httpx.Client(timeout=20) as c:
        if p == "github":
            tok = c.post(PROVIDERS[p]["token"], headers={"Accept": "application/json"},
                         data={"client_id": cid, "client_secret": sec, "code": code, "redirect_uri": _redirect_uri(p)}).json()
            if "access_token" not in tok:
                raise auth.AuthError(f"GitHub said: {tok.get('error_description') or tok.get('error') or 'no token'}")
            u = c.get("https://api.github.com/user", headers={"Authorization": f"Bearer {tok['access_token']}",
                                                               "Accept": "application/vnd.github+json"}).json()
            return {"uid": str(u["id"]), "handle": u.get("login"), "name": u.get("name") or u.get("login") or ""}
        tok = c.post(PROVIDERS[p]["token"], data={"client_id": cid, "client_secret": sec, "code": code,
                                                  "redirect_uri": _redirect_uri(p), "grant_type": "authorization_code"}).json()
        if "access_token" not in tok:
            raise auth.AuthError(f"Google said: {tok.get('error_description') or tok.get('error') or 'no token'}")
        u = c.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {tok['access_token']}"}).json()
        return {"uid": str(u["sub"]), "handle": u.get("email"), "name": u.get("name") or ""}


def callback(p: str, code: str | None, state: str | None, error: str | None = None) -> str:
    """Returns the URL to send the browser to."""
    st = db().get("challenges", f"oauth-{state or '-'}")
    db().delete("challenges", f"oauth-{state or '-'}")
    nxt = _safe_next(st.get("next") if st else None)
    sep = "&" if "?" in nxt else "?"
    if error or not code:
        return f"{nxt}{sep}signin_error={urllib.parse.quote(error or 'cancelled')}"
    if not st or st.get("provider") != p or st["expires"] < time.time():
        return f"{nxt}{sep}signin_error=expired"
    try:
        prof = _profile(p, code)
    except Exception as e:  # noqa: BLE001
        return f"{nxt}{sep}signin_error={urllib.parse.quote(str(e)[:120])}"
    key = f"{p}:{prof['uid']}"
    linked = db().get("identities", key)
    if st.get("link"):
        if linked and linked["observer"] != st["link"]:
            msg = f"that {PROVIDERS[p]['label']} account already belongs to observer {linked['observer']}"
            return f"{nxt}{sep}signin_error={urllib.parse.quote(msg)}"
        db().set("identities", key, {"observer": st["link"], "provider": p, "handle": prof["handle"], "linked_at": now()})
        return f"{nxt}#linked={p}"
    if linked:
        return f"{nxt}#session={auth.new_session(linked['observer'])}"
    claim = secrets.token_urlsafe(24)
    db().set("claims", claim, {"provider": p, "uid": prof["uid"], "handle": prof["handle"], "name": prof["name"][:80],
                               "expires": time.time() + 1800, "next": nxt})
    return f"/observe?claim={claim}" + (f"&then={urllib.parse.quote(nxt)}" if nxt != "/observe" else "")


def suggestions(name: str, handle: str | None) -> list[str]:
    words = re.findall(r"[A-Za-z]+", name or "")
    out = []
    if len(words) >= 2:
        out += [(words[0][0] + words[-1][:2]).upper(), (words[0][0] + words[-1][0]).upper(), (words[0][:2] + words[-1][0]).upper()]
    if words:
        out.append(words[0][:3].upper())
    if handle:
        h = re.sub(r"[^A-Za-z0-9]", "", handle.split("@")[0]).upper()
        if h and h[0].isalpha():
            out += [h[:3], h[:5]]
    seen, free = set(), []
    for c in out:
        if c not in seen and not auth.check_code(c):
            free.append(c)
        seen.add(c)
    return free[:4]


def claim_info(token: str) -> dict:
    c = db().get("claims", token or "-")
    if not c or c["expires"] < time.time():
        raise auth.AuthError("this sign-up link expired; sign in again")
    return {"provider": c["provider"], "label": PROVIDERS[c["provider"]]["label"], "handle": c["handle"], "name": c["name"],
            "suggestions": suggestions(c["name"], c["handle"])}


def claim(token: str, code: str, name: str | None) -> dict:
    c = db().get("claims", token or "-")
    if not c or c["expires"] < time.time():
        raise auth.AuthError("this sign-up link expired; sign in again")
    code = (code or "").strip().upper()
    if why := auth.check_code(code):
        raise ValueError(f"observer code {code}: {why}")
    if db().get("identities", f"{c['provider']}:{c['uid']}"):
        raise ValueError("this account is already linked to an observer; sign in instead")
    obs = {"code": code, "name": (name if name is not None else c["name"])[:80], "created_at": now(), "via": c["provider"]}
    db().set("observers", code, obs)
    db().set("identities", f"{c['provider']}:{c['uid']}", {"observer": code, "provider": c["provider"], "handle": c["handle"], "linked_at": now()})
    db().delete("claims", token)
    return {"token": auth.new_session(code), "observer": auth.public_observer(obs), "next": c.get("next") or "/observe"}


def linked(observer: str) -> list[dict]:
    return [{"provider": x["provider"], "handle": x.get("handle"), "linked_at": x.get("linked_at")} for x in db().where("identities", "observer", observer)]
