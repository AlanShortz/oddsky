"""Oddsky as an OAuth authorization server for MCP clients.

With this, connecting an agent needs no key:

    claude mcp add --transport http oddsky https://oddsky.ai/mcp

The client finds our metadata (/.well-known/oauth-protected-resource/mcp, then
/.well-known/oauth-authorization-server), registers itself, and opens the browser at /authorize. We send
the person to oddsky.ai/observe?authorize=<request>, where they sign in (GitHub, Google or a passkey) and
approve the client for their observer code. The access token it receives is an ordinary instrument key,
so it is listed on their profile and can be revoked like any other.

Instrument keys pasted by hand (`Authorization: Bearer osk_…`) keep working: load_access_token accepts both.
"""

from __future__ import annotations

import os
import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from . import auth
from .db import db
from .ledger import now

SITE = os.environ.get("ODDSKY_SITE", "https://oddsky.ai")
REQUEST_TTL = 900
CODE_TTL = 300


class OddskyOAuth:
    # ---- clients (dynamic registration) ----
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        doc = db().get("oauth_clients", client_id)
        return OAuthClientInformationFull.model_validate(doc) if doc else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        db().set("oauth_clients", client_info.client_id, client_info.model_dump(mode="json", exclude_none=True))

    # ---- the authorization request: hand the person to the website ----
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        rid = secrets.token_urlsafe(18)
        db().set("oauth_requests", rid, {
            "client_id": client.client_id, "client_name": client.client_name or "An MCP client",
            "redirect_uri": str(params.redirect_uri), "explicit": params.redirect_uri_provided_explicitly,
            "code_challenge": params.code_challenge, "state": params.state, "scopes": params.scopes or ["oddsky"],
            "resource": params.resource, "expires": time.time() + REQUEST_TTL,
        })
        return f"{SITE}/observe?authorize={rid}"

    # ---- codes and tokens ----
    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str) -> AuthorizationCode | None:
        doc = db().get("oauth_codes", authorization_code)
        if not doc or doc["client_id"] != client.client_id or doc["expires_at"] < time.time():
            return None
        return AuthorizationCode.model_validate(doc)

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        db().delete("oauth_codes", authorization_code.code)
        if not authorization_code.subject:
            raise TokenError("invalid_grant", "code has no observer")
        k = auth.mint_key(authorization_code.subject, f"{client.client_name or 'MCP client'} (signed in)")
        db().update("keys", auth.sha(k["key"]), {"client_id": client.client_id, "via": "oauth"})
        return OAuthToken(access_token=k["key"], token_type="Bearer", scope=" ".join(authorization_code.scopes))

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        return None  # access tokens are instrument keys and do not expire; revoke them instead

    async def exchange_refresh_token(self, client, refresh_token, scopes) -> OAuthToken:
        raise TokenError("invalid_grant", "refresh tokens are not issued")

    async def load_access_token(self, token: str) -> AccessToken | None:
        if not token.startswith("osk_"):
            return None
        k = db().get("keys", auth.sha(token))
        if not k:
            return None
        return AccessToken(token=token, client_id=k.get("client_id", "instrument-key"), scopes=["oddsky"], subject=k["observer"])

    async def revoke_token(self, token) -> None:
        tok = getattr(token, "token", token)
        db().delete("keys", auth.sha(tok))


# ---- the website's half: show the request, approve or deny it ----------------------------------------

def request_info(rid: str) -> dict:
    r = db().get("oauth_requests", rid or "-")
    if not r or r["expires"] < time.time():
        raise auth.AuthError("this connection request expired; start again from your agent")
    return {"client_name": r["client_name"], "redirect_host": r["redirect_uri"].split("/")[2] if "//" in r["redirect_uri"] else r["redirect_uri"]}


def decide(rid: str, observer: str, allow: bool) -> dict:
    r = db().get("oauth_requests", rid or "-")
    db().delete("oauth_requests", rid or "-")
    if not r or r["expires"] < time.time():
        raise auth.AuthError("this connection request expired; start again from your agent")
    if not allow:
        return {"redirect": construct_redirect_uri(r["redirect_uri"], error="access_denied", state=r.get("state"))}
    code = secrets.token_urlsafe(32)
    db().set("oauth_codes", code, {
        "code": code, "scopes": r["scopes"], "expires_at": time.time() + CODE_TTL, "client_id": r["client_id"],
        "code_challenge": r["code_challenge"], "redirect_uri": r["redirect_uri"],
        "redirect_uri_provided_explicitly": r["explicit"], "resource": r.get("resource"), "subject": observer,
        "issued_at": now(),
    })
    return {"redirect": construct_redirect_uri(r["redirect_uri"], code=code, state=r.get("state"))}


__all__ = ["OddskyOAuth", "request_info", "decide", "AuthorizeError"]
