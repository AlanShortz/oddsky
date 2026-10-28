"""Observers, passkeys, sessions and instrument keys.

An observer is a person (or a lab) with an observer code, like the codes AAVSO gives its observers
(HMB is Franz-Josef Hambsch). There is no email and no password: the code is secured by a passkey.
Agents act for an observer with an instrument key (`osk_…`), sent as `Authorization: Bearer`.
Only hashes of session tokens and keys are stored.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import time

from .db import db
from .ledger import now

RP_ID = os.environ.get("ODDSKY_RP_ID", "oddsky.ai")
ORIGINS = [o.strip() for o in re.split(r"[,;]", os.environ.get("ODDSKY_ORIGINS", "https://oddsky.ai,https://www.oddsky.ai")) if o.strip()]
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,4}$")
RESERVED = {"ODY", "ODDSKY", "ADMIN", "ROOT", "API", "MCP", "SKY", "TEST", "NULL", "NONE", "ANON"}
SESSION_DAYS = 30


class AuthError(Exception):
    status = 401


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def check_code(code: str) -> str | None:
    """None if the code is free and well-formed, else why not."""
    code = (code or "").strip().upper()
    if not CODE_RE.match(code):
        return "2 to 5 letters or digits, starting with a letter"
    if code in RESERVED:
        return "reserved"
    if db().get("observers", code):
        return "taken"
    return None


# ---- passkeys ----------------------------------------------------------------------------------

def register_begin(code: str, name: str = "") -> dict:
    from webauthn import generate_registration_options, options_to_json
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        ResidentKeyRequirement,
        UserVerificationRequirement,
    )

    code = code.strip().upper()
    if why := check_code(code):
        raise AuthError(f"observer code {code}: {why}")
    handle = secrets.token_bytes(16)
    opts = generate_registration_options(
        rp_id=RP_ID, rp_name="Oddsky", user_id=handle, user_name=code, user_display_name=name or code,
        authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED,
                                                               user_verification=UserVerificationRequirement.PREFERRED),
        timeout=180000)
    cid = secrets.token_urlsafe(16)
    db().set("challenges", cid, {"kind": "register", "challenge": b64u(opts.challenge), "code": code, "name": name[:80],
                                 "handle": b64u(handle), "expires": time.time() + 300})
    return {"challenge_id": cid, "options": options_to_json(opts)}


def _take_challenge(cid: str, kind: str) -> dict:
    ch = db().get("challenges", cid or "-")
    db().delete("challenges", cid or "-")
    if not ch or ch.get("kind") != kind or ch.get("expires", 0) < time.time():
        raise AuthError("this sign-in attempt expired; try again")
    return ch


def register_finish(cid: str, credential: dict | str) -> dict:
    from webauthn import verify_registration_response

    ch = _take_challenge(cid, "register")
    if why := check_code(ch["code"]):
        raise AuthError(f"observer code {ch['code']}: {why}")
    v = verify_registration_response(credential=credential, expected_challenge=unb64u(ch["challenge"]),
                                     expected_rp_id=RP_ID, expected_origin=ORIGINS, require_user_verification=False)
    obs = {"code": ch["code"], "name": ch.get("name") or "", "handle": ch["handle"], "created_at": now()}
    db().set("observers", ch["code"], obs)
    db().set("credentials", b64u(v.credential_id), {"observer": ch["code"], "public_key": b64u(v.credential_public_key),
                                                     "sign_count": v.sign_count, "created_at": now()})
    return {"token": new_session(ch["code"]), "observer": public_observer(obs)}


def login_begin() -> dict:
    from webauthn import generate_authentication_options, options_to_json
    from webauthn.helpers.structs import UserVerificationRequirement

    opts = generate_authentication_options(rp_id=RP_ID, user_verification=UserVerificationRequirement.PREFERRED, timeout=180000)
    cid = secrets.token_urlsafe(16)
    db().set("challenges", cid, {"kind": "login", "challenge": b64u(opts.challenge), "expires": time.time() + 300})
    return {"challenge_id": cid, "options": options_to_json(opts)}


def login_finish(cid: str, credential: dict) -> dict:
    from webauthn import verify_authentication_response

    ch = _take_challenge(cid, "login")
    cred_id = credential.get("id") or credential.get("rawId")
    rec = db().get("credentials", cred_id or "-")
    if not rec:
        raise AuthError("this passkey isn't registered with Oddsky")
    v = verify_authentication_response(credential=credential, expected_challenge=unb64u(ch["challenge"]),
                                       expected_rp_id=RP_ID, expected_origin=ORIGINS,
                                       credential_public_key=unb64u(rec["public_key"]),
                                       credential_current_sign_count=rec.get("sign_count", 0), require_user_verification=False)
    db().update("credentials", cred_id, {"sign_count": v.new_sign_count, "last_used": now()})
    obs = db().get("observers", rec["observer"])
    return {"token": new_session(rec["observer"]), "observer": public_observer(obs)}


# ---- sessions and keys ---------------------------------------------------------------------------

def new_session(code: str) -> str:
    tok = "oss_" + secrets.token_urlsafe(32)
    db().set("sessions", sha(tok), {"observer": code, "created_at": now(), "expires": time.time() + SESSION_DAYS * 86400})
    return tok


def end_session(tok: str) -> None:
    db().delete("sessions", sha(tok))


def mint_key(code: str, label: str) -> dict:
    key = "osk_" + secrets.token_urlsafe(30)
    doc = {"observer": code, "label": (label or "my agent").strip()[:60], "created_at": now(), "prefix": key[:10]}
    db().set("keys", sha(key), doc)
    return {"key": key, **doc}


def revoke_key(code: str, prefix: str) -> bool:
    for k in db().where("keys", "observer", code):
        if k.get("prefix") == prefix:
            db().delete("keys", k["_id"])
            return True
    return False


def caller(authorization: str | None) -> dict | None:
    """Resolve 'Bearer <session token or instrument key>' to {observer, via, label}."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    tok = authorization.split(None, 1)[1].strip()
    if tok.startswith("oss_"):
        s = db().get("sessions", sha(tok))
        if s and s.get("expires", 0) > time.time():
            return {"observer": s["observer"], "via": "session", "label": None}
    elif tok.startswith("osk_"):
        k = db().get("keys", sha(tok))
        if k:
            return {"observer": k["observer"], "via": "key", "label": k.get("label")}
    return None


def public_observer(o: dict | None) -> dict | None:
    return {"code": o["code"], "name": o.get("name") or "", "since": o.get("created_at")} if o else None
