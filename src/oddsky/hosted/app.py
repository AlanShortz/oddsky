"""The hosted service: the MCP endpoint and the JSON API in one ASGI app.

    /mcp            the observatory over Streamable HTTP (stateless), for any MCP client
    /api/...        observers, passkeys, keys, notebooks, the Sky Ledger, the docket

    uvicorn oddsky.hosted.app:app --port 8080
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
import time
from collections import defaultdict, deque
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from .. import __version__
from ..case.store import CaseStore
from ..paths import workspace
from ..tools import OPEN_TOOLS, Toolbox
from . import auth, identity, notebooks, oauth_server, sky
from .db import db
from .ledger import verify

log = logging.getLogger("oddsky.hosted")
ADMIN = os.environ.get("ODDSKY_ADMIN_TOKEN")
SITE = os.environ.get("ODDSKY_SITE", "https://oddsky.ai")

INSTRUCTIONS = """You are connected to Oddsky, an open observatory: real telescope data on strange stars and the
tools to analyse it. You are working for an Oddsky observer, in their notebook. Work like a careful
scientist: case_overview first, then skeptic_report, look at the light curves, and only then propose
hypotheses. Record findings with add_claim, tagging each claim honestly (observed | computed | inferred
| speculated) and citing the call_id of the tool results it rests on. Propose explanations with
add_hypothesis (classes from list_classes) and say what would falsify each.

register_prediction seals a machine-checkable prediction on the public Sky Ledger at once: it is
hash-chained, cannot be edited or withdrawn, and the archive grades it automatically when its window
closes. There are no private predictions. Pass `model` (the model you are) so the scoreboard can
credit it. Only seal what you would bet on, with an honest probability: calibration is the score.

When you have something worth showing, publish_notebook makes a public page of the claims,
hypotheses, predictions and the ledger of tool calls they rest on. Never call anything a discovery.
The first principle is that you must not fool yourself, and you are the easiest person to fool."""

RECORDING = {"add_claim", "retract_claim", "add_hypothesis", "update_hypothesis", "register_prediction", "check_prediction"}
NO_KEY = (f"Oddsky's hosted observatory needs an instrument key. Get one in a minute at {SITE}/observe "
          "(choose an observer code, make a passkey, mint a key), then reconnect with the header "
          "'Authorization: Bearer osk_…'. Without one you can still read every case at "
          f"{SITE}/llms.txt.")

# per-observer rate limits (per instance): calls per hour
LIMITS = {"open_case": 6, "*": 600}
_calls: dict[tuple[str, str], deque] = defaultdict(deque)


def _limit(observer: str, tool: str) -> None:
    key = (observer, tool if tool in LIMITS else "*")
    q, cap, t = _calls[key], LIMITS.get(tool, LIMITS["*"]), time.time()
    while q and q[0] < t - 3600:
        q.popleft()
    if len(q) >= cap:
        raise PermissionError(f"rate limit: {cap} {tool if tool in LIMITS else 'tool'} calls per hour")
    q.append(t)


def _who(ctx: Context) -> dict:
    c = auth.caller((ctx.headers or {}).get("authorization"))
    if not c:
        raise PermissionError(NO_KEY)
    return c


def _target_name(cid: str, observer: str) -> str | None:
    try:
        c = CaseStore(notebooks.root(observer) / "cases" / cid).load()
        return c.target.name if c.target else None
    except Exception:
        return None


def build() -> MCPServer:
    from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions

    # Oddsky is its own OAuth authorization server, so `claude mcp add --transport http oddsky
    # https://oddsky.ai/mcp` needs no key: the client opens the browser and the person signs in.
    mcp = MCPServer("oddsky", title="Oddsky", instructions=INSTRUCTIONS, version=__version__, website_url=SITE,
                    auth_server_provider=oauth_server.OddskyOAuth(),
                    auth=AuthSettings(issuer_url=SITE, resource_server_url=f"{SITE}/mcp", service_documentation_url=f"{SITE}/agents",
                                      client_registration_options=ClientRegistrationOptions(enabled=True, valid_scopes=["oddsky"], default_scopes=["oddsky"]), validate_token_resource=False,
                                      revocation_options=RevocationOptions(enabled=True)))

    def run_tool(name: str, ctx: Context, kwargs: dict, model: str | None = None) -> Any:
        who = _who(ctx)
        obs = who["observer"]
        _limit(obs, name)
        author = f"{obs}/{model or who.get('label') or 'agent'}"
        tb = Toolbox(mode="open", author=author)
        case = kwargs.get("case")
        if case is not None:
            kwargs["case"] = case = notebooks.ensure(obs, case)
        with workspace(notebooks.root(obs), case_prefix=obs):
            result = getattr(tb, name)(**kwargs)
            if name == "open_case":
                notebooks.sync(obs, result["case"], everything=True)
                return result
            if case is not None:
                notebooks.sync(obs, case)
            if name == "register_prediction":
                c = CaseStore(notebooks.root(obs) / "cases" / case).load()
                p = next(x for x in c.predictions if x.id == result["prediction"])
                e = sky.seal(observer=obs, agent=who.get("label"), model=model, case=case,
                             target=c.target.name if c.target else None, prediction=p.model_dump(mode="json"))
                result = {**result, "sealed": {"seq": e["seq"], "hash": e["hash"], "ledger": f"{SITE}/ledger#seq-{e['seq']}",
                                               "note": "Sealed on the public Sky Ledger. It cannot be edited or withdrawn."}}
        return result

    for name in OPEN_TOOLS:
        if name == "list_cases":
            continue
        fn = getattr(Toolbox, name)
        sig = inspect.signature(fn)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        extra = []
        if name == "register_prediction":
            extra.append(inspect.Parameter("model", inspect.Parameter.KEYWORD_ONLY, default="", annotation="str"))
        extra.append(inspect.Parameter("ctx", inspect.Parameter.KEYWORD_ONLY, annotation=Context))

        def make(name=name):
            def tool(**kw):
                ctx = kw.pop("ctx")
                model = kw.pop("model", None) or None
                return run_tool(name, ctx, kw, model)
            return tool

        t = make()
        t.__name__ = name
        t.__doc__ = fn.__doc__ + ("\n\nmodel: the model you are (e.g. claude-opus-5.5), credited on the public scoreboard."
                                  if name == "register_prediction" else "")
        t.__signature__ = sig.replace(parameters=[*params, *extra])
        t.__annotations__ = {**{k: v for k, v in fn.__annotations__.items() if k != "return"}, "ctx": Context,
                             **({"model": "str"} if name == "register_prediction" else {})}
        mcp.tool(name=name)(t)

    @mcp.tool()
    def list_cases(ctx: Context) -> dict:
        """List the cases you can investigate: the Oddsky casebook, plus cases in your own notebook."""
        who = _who(ctx)
        out = []
        with workspace(notebooks.CANON.parent):
            for d in sorted(notebooks.CANON.glob("OS-*")):
                c = CaseStore(d).load()
                out.append({"case": c.id, "title": c.title, "status": c.status, "hook": c.hook})
        mine = [c for c in notebooks.own_cases(who["observer"]) if not (notebooks.CANON / c).exists()]
        return {"casebook": out, "your_cases": mine, "note": "Casebook cases are copied into your notebook the first time you touch them."}

    @mcp.tool()
    def whoami(ctx: Context) -> dict:
        """Which observer you are working for, and where your work shows up."""
        who = _who(ctx)
        return {"observer": who["observer"], "instrument": who.get("label"), "profile": f"{SITE}/observe",
                "sky_ledger": f"{SITE}/ledger", "notebook_cases": notebooks.own_cases(who["observer"])}

    @mcp.tool()
    def publish_notebook(case: str, title: str, summary: str, ctx: Context) -> dict:
        """Publish your notebook for one case as a public page: your summary (Markdown; cite claims as
        [C3] and tool calls as (K12)), and every claim, hypothesis, prediction and ledger entry behind it.
        Publish when you have something worth checking, including a negative result."""
        who = _who(ctx)
        cid = notebooks.ensure(who["observer"], case)
        return notebooks.publish(who["observer"], cid, title, summary, who.get("label"))

    @mcp.tool()
    def sky_ledger(ctx: Context, limit: int = 20) -> dict:
        """The most recent predictions sealed on the public Sky Ledger, and the scoreboard."""
        _who(ctx)
        d = sky.docket()
        return {"head": d["head"], "recent": [{k: s.get(k) for k in ("seq", "observer", "model", "case", "target", "statement",
                                                                      "probability", "resolve_by", "outcome")}
                                               for s in d["items"][-limit:]], "scoreboard": d["board"]}

    _routes(mcp)
    return mcp


# ---- JSON API --------------------------------------------------------------------------------------

def _json(data, status=200):
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


def _api(fn):
    @functools.wraps(fn)
    async def h(request: Request):
        try:
            return await fn(request)
        except auth.AuthError as e:
            return _json({"error": str(e)}, 401)
        except (ValueError, KeyError) as e:
            return _json({"error": str(e)}, 400)
        except PermissionError as e:
            return _json({"error": str(e)}, 403)
        except Exception as e:  # noqa: BLE001
            log.exception("api error")
            return _json({"error": f"{type(e).__name__}: {e}"[:300]}, 500)
    return h


async def _body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _me(request: Request) -> dict:
    c = auth.caller(request.headers.get("authorization"))
    if not c or c["via"] != "session":
        raise auth.AuthError("sign in first")
    return c


def _admin(request: Request) -> None:
    if not ADMIN or request.headers.get("x-oddsky-admin") != ADMIN:
        raise PermissionError("admin only")


def _routes(mcp: MCPServer) -> None:
    r = mcp.custom_route

    @r("/api/health", methods=["GET"])
    async def health(request):
        return _json({"ok": True, "version": __version__, "head": db().head()})

    @r("/api/auth/providers", methods=["GET"])
    @_api
    async def providers(request):
        return _json({"providers": identity.enabled(), "passkeys": True})

    @r("/api/oauth/{provider}/start", methods=["GET"])
    async def oauth_start(request):
        from starlette.responses import RedirectResponse

        try:
            url = identity.start(request.path_params["provider"], request.query_params.get("next"))
        except ValueError as e:
            return RedirectResponse(f"/observe?signin_error={str(e)}", status_code=302)
        return RedirectResponse(url, status_code=302)

    @r("/api/oauth/{provider}/link", methods=["POST"])
    @_api
    async def oauth_link(request):
        c = _me(request)
        return _json({"url": identity.link_intent(request.path_params["provider"], c["observer"], (await _body(request)).get("next"))})

    @r("/api/oauth/{provider}/callback", methods=["GET"])
    async def oauth_callback(request):
        import anyio
        from starlette.responses import RedirectResponse

        q = request.query_params
        url = await anyio.to_thread.run_sync(lambda: identity.callback(request.path_params["provider"], q.get("code"), q.get("state"), q.get("error")))
        return RedirectResponse(url, status_code=302)

    @r("/api/claim/{token}", methods=["GET"])
    @_api
    async def claim_info(request):
        return _json(identity.claim_info(request.path_params["token"]))

    @r("/api/claim", methods=["POST"])
    @_api
    async def claim(request):
        b = await _body(request)
        return _json(identity.claim(b.get("token"), b.get("code"), b.get("name")))

    @r("/api/passkeys/begin", methods=["POST"])
    @_api
    async def passkey_begin(request):
        return _json(auth.add_passkey_begin(_me(request)["observer"]))

    @r("/api/passkeys/finish", methods=["POST"])
    @_api
    async def passkey_finish(request):
        b = await _body(request)
        return _json(auth.add_passkey_finish(_me(request)["observer"], b.get("challenge_id"), b.get("credential") or {}))

    @r("/api/authorize/{rid}", methods=["GET"])
    @_api
    async def authorize_info(request):
        return _json(oauth_server.request_info(request.path_params["rid"]))

    @r("/api/authorize/{rid}", methods=["POST"])
    @_api
    async def authorize_decide(request):
        c = _me(request)
        return _json(oauth_server.decide(request.path_params["rid"], c["observer"], bool((await _body(request)).get("allow"))))

    @r("/api/observers/check", methods=["POST"])
    @_api
    async def check(request):
        code = (await _body(request)).get("code", "")
        return _json({"code": code.strip().upper(), "problem": auth.check_code(code)})

    @r("/api/register/begin", methods=["POST"])
    @_api
    async def reg_begin(request):
        b = await _body(request)
        return _json(auth.register_begin(b.get("code", ""), b.get("name", "")))

    @r("/api/register/finish", methods=["POST"])
    @_api
    async def reg_finish(request):
        b = await _body(request)
        return _json(auth.register_finish(b.get("challenge_id"), b.get("credential")))

    @r("/api/login/begin", methods=["POST"])
    @_api
    async def login_begin(request):
        return _json(auth.login_begin())

    @r("/api/login/finish", methods=["POST"])
    @_api
    async def login_finish(request):
        b = await _body(request)
        return _json(auth.login_finish(b.get("challenge_id"), b.get("credential") or {}))

    @r("/api/logout", methods=["POST"])
    @_api
    async def logout(request):
        a = request.headers.get("authorization", "")
        if a.lower().startswith("bearer "):
            auth.end_session(a.split(None, 1)[1])
        return _json({"ok": True})

    @r("/api/me", methods=["GET"])
    @_api
    async def me(request):
        c = _me(request)
        code = c["observer"]
        keys = [{k: x.get(k) for k in ("label", "prefix", "created_at", "via")} for x in db().where("keys", "observer", code)]
        nbs = [{k: x.get(k) for k in ("id", "title", "case", "published_at")} for x in db().where("notebooks", "observer", code)]
        seals = [s for s in sky.docket()["items"] if s["observer"] == code]
        return _json({"observer": auth.public_observer(db().get("observers", code)), "keys": keys, "notebooks": nbs,
                      "seals": seals, "notebook_cases": notebooks.own_cases(code), "identities": identity.linked(code),
                      "passkeys": len(db().where("credentials", "observer", code)), "providers": identity.enabled()})

    @r("/api/keys", methods=["POST"])
    @_api
    async def keys(request):
        c = _me(request)
        return _json(auth.mint_key(c["observer"], (await _body(request)).get("label", "")))

    @r("/api/keys/revoke", methods=["POST"])
    @_api
    async def revoke(request):
        c = _me(request)
        return _json({"revoked": auth.revoke_key(c["observer"], (await _body(request)).get("prefix", ""))})

    @r("/api/observers/{code}", methods=["GET"])
    @_api
    async def observer(request):
        code = request.path_params["code"].upper()
        o = db().get("observers", code)
        if not o and code != "ODY":
            return _json({"error": "no such observer"}, 404)
        nbs = [{k: x.get(k) for k in ("id", "title", "case", "published_at")} for x in db().where("notebooks", "observer", code)]
        seals = [s for s in sky.docket()["items"] if s["observer"] == code]
        return _json({"observer": auth.public_observer(o) or {"code": "ODY", "name": "Oddsky (imported from git)"},
                      "notebooks": nbs, "seals": seals})

    @r("/api/notebooks", methods=["GET"])
    @_api
    async def notebooks_list(request):
        rows = sorted(db().all("notebooks", limit=500), key=lambda x: x.get("published_at", ""), reverse=True)
        return _json({"notebooks": [{k: x.get(k) for k in ("id", "title", "observer", "agent", "case", "case_title", "published_at")} for x in rows]})

    @r("/api/notebooks/{id}", methods=["GET"])
    @_api
    async def notebook(request):
        n = db().get("notebooks", request.path_params["id"])
        return _json(n) if n else _json({"error": "no such notebook"}, 404)

    @r("/api/ledger", methods=["GET"])
    @_api
    async def ledger(request):
        after = int(request.query_params.get("after", 0))
        limit = min(5000, int(request.query_params.get("limit", 1000)))
        rows = db().log_range(after, limit)
        if request.query_params.get("format") == "jsonl":
            import json as _j

            return PlainTextResponse("".join(_j.dumps(e, ensure_ascii=False) + "\n" for e in rows), media_type="application/x-ndjson")
        return _json({"head": db().head(), "entries": rows})

    @r("/api/ledger/verify", methods=["GET"])
    @_api
    async def ledger_verify(request):
        rows = db().log_range(0, 100000)
        return _json({**verify(rows), "head": db().head()})

    @r("/api/docket", methods=["GET"])
    @_api
    async def docket_(request):
        return _json(sky.docket())

    @r("/api/admin/genesis", methods=["POST"])
    @_api
    async def genesis(request):
        _admin(request)
        if db().head()["seq"]:
            raise ValueError("the ledger already has entries; genesis runs once")
        out = []
        for it in (await _body(request)).get("items", []):
            e = sky.seal(observer="ODY", agent=it.get("agent"), model=it.get("model"), case=it["case"], target=it.get("target"),
                         prediction=it["prediction"], source=it.get("source", "git"), at=it.get("at"),
                         extra={k: it[k] for k in ("trial", "packet", "provenance") if k in it})
            if it.get("outcome") in ("true", "false", "unresolvable"):
                sky.grade_entry(e, it["outcome"], it.get("observed"), it.get("n_points", 0), it.get("note", ""),
                                source=it.get("graded_by", "trial-scorer"), at=it.get("graded_at"))
            out.append(e["seq"])
        return _json({"sealed": out, "head": db().head()})

    @r("/api/admin/invite", methods=["POST"])
    @_api
    async def invite(request):
        """Create an observer without a passkey (for a collaborator, or a lab's bot) and mint a key.
        They can add a passkey later by signing in with the key on /observe."""
        _admin(request)
        b = await _body(request)
        code = b.get("code", "").strip().upper()
        if not db().get("observers", code):
            if why := auth.check_code(code):
                raise ValueError(f"{code}: {why}")
            db().set("observers", code, {"code": code, "name": b.get("name", ""), "created_at": sky.now(), "invited": True})
        return _json(auth.mint_key(code, b.get("label", "invited")))

    @r("/api/admin/grade", methods=["POST"])
    @_api
    async def grade(request):
        _admin(request)
        import anyio

        dry = request.query_params.get("dry_run") == "1"
        return _json({"results": await anyio.to_thread.run_sync(lambda: sky.grade_due(dry_run=dry))})


def create_app():
    from mcp.server.transport_security import TransportSecuritySettings

    mcp = build()
    app = mcp.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0",
                                  transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
    return app


app = create_app()

