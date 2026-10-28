#!/usr/bin/env python3
"""Build the public site (oddsky.ai) from the repo into dist/.

    python3 site/build.py            # writes dist/
    python3 site/build.py --serve    # and serves it on http://localhost:8765 with clean URLs

Standard library only, Python 3.9+ (keep it that way: no datetime.UTC), so Vercel's build image can run it with no install step.

The site is the static viewer in web/ plus what a public site needs and a hash-routed viewer can't do:

- a real URL per page (/case/OS-0014), each with its own title, description and link-preview image,
  and a text prerender so link scrapers, search engines and agents that don't run JavaScript see content;
- data/hunts.json (site/hunts.json plus each hunt's README) and data/docket.json (every sealed
  prediction across cases and trials), and docket.ics so anyone can put the sky's grading days in
  their calendar;
- an agent door: /llms.txt, and a Markdown dossier per case (/case/OS-0014.md) and per hunt, so any
  agent that can fetch a URL can investigate without installing anything.

Nothing in web/ is modified. web/data/ is written by `oddsky export-web`.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DIST = ROOT / "dist"
SITE_URL = os.environ.get("ODDSKY_SITE_URL", "https://oddsky.ai").rstrip("/")
REPO = "https://github.com/oddsky-org/oddsky"
MCP_CMD = "claude mcp add oddsky -- uvx oddsky mcp"
TAGLINE = "The universe is an open question."
DEFAULT_DESC = ("An open observatory your AI agent can use. Real telescope data on strange stars, "
                "and findings anyone can check: every claim tagged, every number with a receipt, "
                "every prediction sealed and graded by the sky.")


# ---- helpers ------------------------------------------------------------------------------------

def esc(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def mjd_to_date(mjd: float) -> date:
    return (datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(days=float(mjd))).date()


def mjd_to_year(mjd: float) -> float:
    return 2000 + (float(mjd) - 51544.5) / 365.25


def plain(md: str) -> str:
    """Markdown → one plain line, for meta descriptions."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md or "")
    s = re.sub(r"[*_`#>]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def clip(s: str, n: int = 200) -> str:
    s = plain(s)
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fmt_int(n) -> str:
    return f"{int(n):,}"


def pct(p) -> str:
    return "–" if p is None else f"{round(float(p) * 100)}%"


# ---- load --------------------------------------------------------------------------------------

def load_cases() -> tuple[dict, dict]:
    index = json.loads((WEB / "data" / "index.json").read_text())
    cases = {}
    for c in index.get("cases", []):
        p = WEB / "data" / "cases" / f"{c['id']}.json"
        if p.exists():
            cases[c["id"]] = json.loads(p.read_text())
    return index, cases


def rewrite_readme_links(md: str, hunt_id: str) -> str:
    """Repo-relative links in a hunt README → site routes or GitHub."""
    def fix(m):
        text, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#)", url):
            return m.group(0)
        case = re.search(r"cases/(OS-\d+)/?$", url)
        if case:
            return f"[{text}](/case/{case.group(1)})"
        hunt = re.search(r"hunts/(H-\d+)/?$", url)
        if hunt:
            return f"[{text}](/hunt/{hunt.group(1)})"
        path = os.path.normpath(f"hunts/{hunt_id}/{url}")
        return f"[{text}]({REPO}/tree/main/{path})"
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", fix, md)


def load_hunts() -> list:
    spec = json.loads((ROOT / "site" / "hunts.json").read_text())
    out = []
    for hunt in spec["hunts"]:
        d = ROOT / "hunts" / hunt["id"]
        if not d.is_dir():
            continue
        readme = d / "README.md"
        hunt = dict(hunt)
        hunt["readme"] = rewrite_readme_links(readme.read_text(), hunt["id"]) if readme.exists() else None
        out.append(hunt)
    return out, spec.get("wrong", [])


# ---- the living sky -------------------------------------------------------------------------------

SKY_T0, SKY_T1, SKY_STEP = 2010.0, 2026.95, 0.05  # years; ~18-day bins


def sky_cases(index: dict, cases: dict) -> dict:
    """Each case's position and optical light curve as one brightness series on a shared time grid,
    for the home page sky: every optical series relative to its own median, merged, binned (median)."""
    import statistics

    n = int(round((SKY_T1 - SKY_T0) / SKY_STEP)) + 1
    out = []
    meta = {c["id"]: c for c in index.get("cases", [])}
    for cid, payload in cases.items():
        c = payload.get("case", {})
        t = c.get("target") or {}
        if t.get("ra") is None:
            continue
        bins: list[list[float]] = [[] for _ in range(n)]
        used = []
        for key, sr in (payload.get("series") or {}).items():
            if key.split(":")[0] in ("NEOWISE", "NEOWISE_EXP", "TESS") or len(sr.get("t") or []) < 8:
                continue
            mags = [m for m in sr["mag"] if m is not None]
            if not mags:
                continue
            base = statistics.median(mags)
            used.append(key)
            for tt, m in zip(sr["t"], sr["mag"]):
                if m is None:
                    continue
                i = int((mjd_to_year(tt) - SKY_T0) / SKY_STEP)
                if 0 <= i < n:
                    bins[i].append(m - base)
        dm = [round(statistics.median(b), 2) if b else None for b in bins]
        out.append({"id": cid, "title": c.get("title"), "hook": plain(c.get("hook") or ""), "target": t.get("name"),
                    "ra": t["ra"], "dec": t["dec"], "status": c.get("status"), "series": used,
                    "control": cid in ("OS-0008", "OS-0009"), "dm": dm, "featured": bool(meta.get(cid, {}).get("featured"))})
    return {"t0": SKY_T0, "step": SKY_STEP, "cases": out}


# ---- the docket ----------------------------------------------------------------------------------

def build_docket(index: dict, cases: dict) -> list:
    """Every sealed prediction, from cases and from trial hindsight forecasts, resolved or not."""
    items = []
    meta = {c["id"]: c for c in index.get("cases", [])}
    for cid, payload in cases.items():
        c = payload.get("case", {})
        for p in c.get("predictions") or []:
            ch = p.get("check") or {}
            r = p.get("resolution") or {}
            items.append({
                "source": "case", "case": cid, "target": meta[cid].get("target"), "case_title": c.get("title"),
                "id": p.get("id"), "statement": p.get("statement"), "probability": p.get("probability"),
                "author": p.get("author"), "registered_at": (p.get("registered_at") or "")[:10],
                "resolve_by": p.get("resolve_by"),
                "window": [mjd_to_date(ch["start"]).isoformat(), mjd_to_date(ch["end"]).isoformat()] if "start" in ch else None,
                "outcome": r.get("outcome", "pending"), "note": r.get("note"),
                "href": f"/case/{cid}#pred-{p.get('id')}",
            })
    for sc in index.get("scorecards", []):
        packets = {x.get("case"): x for x in sc.get("cases", [])}
        trial = sc.get("trial", "trial")
        for p in sc.get("predictions") or []:
            pk = packets.get(p.get("case"), {})
            real = pk.get("real_case")
            m = re.search(r"MJD\s*(\d+(?:\.\d+)?)", p.get("note") or "")
            closes = mjd_to_date(float(m.group(1))).isoformat() if m else None
            items.append({
                "source": "trial", "trial": trial, "packet": p.get("case"), "case": real,
                "target": meta.get(real, {}).get("target"), "case_title": meta.get(real, {}).get("title"),
                "id": p.get("id"), "statement": p.get("statement"), "probability": p.get("probability"),
                "author": sc.get("agent"), "registered_at": sc.get("run_at"),
                "resolve_by": closes if p.get("outcome") == "pending" else None,
                "window": None, "outcome": p.get("outcome"), "note": p.get("note"),
                "brier": p.get("brier"), "href": "/trials",
            })
    items.sort(key=lambda x: (x["outcome"] != "pending", x["resolve_by"] or "9999", x.get("case") or "", x["id"] or ""))
    return items


def ics_escape(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")


def ics_fold(line: str) -> str:
    out, b = [], line.encode("utf-8")
    while len(b) > 74:
        cut = 74
        while (b[cut] & 0xC0) == 0x80:  # don't split a UTF-8 sequence
            cut -= 1
        out.append(b[:cut].decode())
        b = b" " + b[cut:]
    out.append(b.decode())
    return "\r\n".join(out)


def build_ics(docket: list) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Oddsky//The Docket//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:Oddsky: the sky grades us",
             "X-WR-CALDESC:Every sealed Oddsky prediction\\, on the day the sky answers it.",
             "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]
    for d in docket:
        if d["outcome"] != "pending" or not d["resolve_by"]:
            continue
        day = date.fromisoformat(d["resolve_by"])
        who = d.get("target") or d.get("case") or "a strange star"
        tag = f"{d['case']} {d['id']}" if d["source"] == "case" else f"{d['trial']} {d['packet']} {d['id']}"
        desc = (f"{d['statement']}\n\nSealed {d['registered_at']} by {d['author']}, who gave it {pct(d['probability'])}. "
                f"The archive checks it by itself; nobody grades their own homework.\n\n{SITE_URL}{d['href']}")
        summary = f"The sky grades {who}: {tag} ({pct(d['probability'])})"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{re.sub(r'[^A-Za-z0-9-]', '-', tag)}@oddsky.ai",
            f"DTSTAMP:{(d['registered_at'] or '2026-10-27').replace('-', '')}T000000Z",
            f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(day + timedelta(days=1)).strftime('%Y%m%d')}",
            ics_fold(f"SUMMARY:{ics_escape(summary)}"),
            ics_fold(f"DESCRIPTION:{ics_escape(desc)}"),
            f"URL:{SITE_URL}{d['href']}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# ---- Markdown for agents -------------------------------------------------------------------------

AGENT_RULES = """\
## House rules for agents

1. **Tag every claim** as `observed` (read straight off the data), `computed` (derived by code someone can rerun),
   `inferred` (a reasoned step beyond the data) or `speculated` (an idea worth testing, not yet evidence).
2. **Give receipts.** Say which series, which time window and which statistic every number came from.
3. **Run the Skeptic's questions first.** Is a neighbour blended into the beam? Is a period just the survey's cadence
   or the Moon? Did more than one instrument see it? Did the series start mid-event?
4. **Try to break the leading hypothesis** before you add to it. A hypothesis that predicts nothing can't lose.
5. **Never call something a discovery.** Say what would have to be true, and what observation would prove it wrong.
6. **Credit observers.** AAVSO data are measurements by named amateur astronomers; the dossier lists them.
"""

SERIES_NOTE = """\
Each light curve is `series["<SURVEY>:<band>"]` in the case JSON, with parallel arrays: `t` (MJD; calendar year =
2000 + (MJD − 51544.5)/365.25), `mag` (magnitudes: larger is fainter), `err` (1σ), and `flagged` (points removed
by quality cuts, each with a reason). Dense series are binned; `binned_days` says how. `context.gaia` holds
Gaia DR3 parameters, `context.neighbors` the Gaia sources nearby, `skeptic.checks` the artifact checks, and
`provenance` the exact archive queries and every cut applied.
"""


def case_markdown(cid: str, payload: dict, meta: dict) -> str:
    c = payload.get("case", {})
    t = c.get("target", {}) or {}
    g = (payload.get("context") or {}).get("gaia") or {}
    L = [f"# {cid}: {c.get('title') or t.get('name')}", ""]
    if c.get("hook"):
        L += [f"> {plain(c['hook'])}", ""]
    L += [f"- **Star:** {t.get('name', '?')}" + (f" ({', '.join(t.get('aliases', []))})" if t.get("aliases") else ""),
          f"- **Position (J2000, deg):** RA {t.get('ra')}, Dec {t.get('dec')}",
          f"- **Status on the discovery ladder:** {c.get('status')} "
          "(observation → anomaly → reproduced → interpreted → validated; exits: artifact, closed)",
          f"- **Web page:** {SITE_URL}/case/{cid}",
          f"- **All data (JSON, ~0.1-0.5 MB):** {SITE_URL}/data/cases/{cid}.json",
          f"- **Case directory in git:** {REPO}/tree/main/cases/{cid}", ""]
    if g:
        keys = [("G", "Gaia G mag"), ("bp_rp", "BP−RP"), ("teff_gspphot", "Teff (K)"), ("distance_pc", "distance (pc)"),
                ("abs_G", "absolute G"), ("ruwe", "RUWE"), ("non_single_star", "non_single_star")]
        L += ["## Gaia DR3", "", "| quantity | value |", "|---|---|"]
        for k, label in keys:
            v = g.get(k)
            if v is not None:
                L.append(f"| {label} | {round(v, 3) if isinstance(v, float) else v} |")
        L.append("")
    if c.get("summary"):
        L += ["## Where the argument stands", "", c["summary"].strip(), ""]
    ser = payload.get("series") or {}
    if ser:
        L += ["## Light curves", "", SERIES_NOTE, "| series | points | span | flagged |", "|---|---|---|---|"]
        for k, s in ser.items():
            tt = s.get("t") or []
            if not tt:
                continue
            span = f"{mjd_to_date(min(tt)).isoformat()} to {mjd_to_date(max(tt)).isoformat()}"
            L.append(f"| `{k}` | {len(tt)} | {span} | {len(s.get('flagged') or [])} |")
        L.append("")
    sk = payload.get("skeptic") or {}
    if sk.get("checks"):
        L += ["## The Skeptic (deterministic artifact checks)", "", f"{sk.get('summary', '')}", ""]
        for ch in sk["checks"]:
            L.append(f"- **{ch.get('status', '?').upper()}** {ch.get('title')}: {plain(ch.get('finding') or '')}")
        L.append("")
    if c.get("claims"):
        L += ["## Claims so far", ""]
        for cl in c["claims"]:
            mark = " ~~retracted~~" if cl.get("retracted") else ""
            L.append(f"- **{cl['id']}** `{cl.get('tag', 'untagged')}`{mark} {plain(cl.get('text', ''))}"
                     + (f" (receipts: {', '.join(cl['calls'])})" if cl.get("calls") else ""))
        L.append("")
    if c.get("hypotheses"):
        L += ["## Hypotheses", ""]
        for hy in c["hypotheses"]:
            L.append(f"- **{hy['id']}** ({hy.get('klass')}, {hy.get('status', 'live')}): {plain(hy.get('statement', ''))}")
            if hy.get("would_falsify"):
                L.append(f"  - *Would falsify:* {plain(hy['would_falsify'])}")
        L.append("")
    if c.get("predictions"):
        L += ["## Sealed predictions", ""]
        for p in c["predictions"]:
            r = p.get("resolution") or {}
            L.append(f"- **{p['id']}** ({pct(p.get('probability'))}, sealed {str(p.get('registered_at', ''))[:10]} by "
                     f"{p.get('author')}, resolves by {p.get('resolve_by')}; {r.get('outcome', 'pending')}): {plain(p.get('statement', ''))}")
        L.append("")
    for rv in payload.get("reviews") or []:
        md = rv.get("markdown", "")
        # the verdict paragraph(s): from "## Verdict" to the next heading
        m = re.search(r"##\s*Verdict\s*\n(.*?)(?=\n##\s|\Z)", md, flags=re.S)
        L += [f"## Referee report ({rv.get('file', '')})", "",
              "An independent, adversarial pass whose job was to break the case. Verdict:", "",
              (m.group(1).strip() if m else plain(md[:1200])), "",
              f"Full report: {SITE_URL}/data/cases/{cid}.json (key `reviews`) or {REPO}/tree/main/cases/{cid}/reviews", ""]
    if c.get("literature"):
        L += ["## Literature", ""] + [f"- {x.get('note', '')} ({x.get('bibcode', '')})" for x in c["literature"]] + [""]
    L += ["## Investigate", "",
          f"Read the JSON above and work from the data. To run the full observatory (archive queries, periodograms, "
          f"the Skeptic, recorded claims and sealed predictions), install the MCP server: `{MCP_CMD}`, then "
          f"\"Open Oddsky case {cid}. Run the skeptic first, then try to break the leading hypothesis.\"", "",
          AGENT_RULES]
    return "\n".join(L)


def llms_txt(index: dict, cases: dict, hunts: list, docket: list) -> str:
    L = ["# Oddsky", "",
         f"> {TAGLINE} Oddsky is an open observatory that AI agents can use: real telescope data on strange stars "
         "(Gaia, NEOWISE, AAVSO, TESS, ZTF, ATLAS, ASAS-SN), a deterministic Skeptic, and cases kept in git, where every "
         "claim is tagged with how we know it and every prediction is sealed in advance and graded by the sky.", "",
         "You can investigate without installing anything: every case has a Markdown dossier and a JSON file with all of its "
         "light curves. Start with the dossier, then work from the data. If you can run tools, the hosted MCP server gives you "
         f"the whole observatory: `{SITE_URL}/mcp` (Streamable HTTP with MCP sign-in: your human approves you once in the browser), "
         f"or run it locally with `{MCP_CMD}`. Predictions sealed through the hosted server go on the public, hash-chained "
         f"Sky Ledger ({SITE_URL}/ledger) and are graded automatically by the archives.", "",
         AGENT_RULES,
         "## Cases", ""]
    for c in index.get("cases", []):
        if c["id"] not in cases:
            continue
        L.append(f"- [{c['id']}: {c.get('title') or c.get('target')}]({SITE_URL}/case/{c['id']}.md): "
                 f"{c.get('target')}, {c.get('status')}. {clip(c.get('hook') or '', 160)} "
                 f"(data: {SITE_URL}/data/cases/{c['id']}.json)")
    L += ["", "## Hunts (sky-wide searches)", ""]
    for hu in hunts:
        L.append(f"- [{hu['id']}: {hu['title']}]({SITE_URL}/hunt/{hu['id']}.md): {hu['verdict']}")
    pending = [d for d in docket if d["outcome"] == "pending"]
    L += ["", "## The Docket", "",
          f"{len(pending)} sealed predictions are waiting for the sky: {SITE_URL}/data/docket.json "
          f"(calendar: {SITE_URL}/docket.ics).", "",
          "## Optional", "",
          f"- [How Oddsky keeps itself honest]({REPO}/blob/main/docs/EPISTEMICS.md)",
          f"- [Manifesto]({REPO}/blob/main/docs/MANIFESTO.md)",
          f"- [Strange Stars Trial 001 scorecards]({SITE_URL}/trials)",
          f"- [Source code]({REPO})", ""]
    return "\n".join(L)


# ---- HTML pages ----------------------------------------------------------------------------------

def prerender_case(cid: str, payload: dict) -> str:
    c = payload.get("case", {})
    parts = [f"<p class='kicker'>Case file {esc(cid)} · {esc((c.get('target') or {}).get('name'))} · {esc(c.get('status'))}</p>",
             f"<h1>{esc(c.get('title'))}</h1>", f"<p>{esc(plain(c.get('hook') or ''))}</p>"]
    for para in (c.get("summary") or "").split("\n\n"):
        if para.strip():
            parts.append(f"<p>{esc(plain(para))}</p>")
    if c.get("claims"):
        parts.append("<h2>Claims</h2><ul>" + "".join(
            f"<li><b>{esc(x['id'])}</b> [{esc(x.get('tag'))}] {esc(plain(x.get('text', '')))}</li>" for x in c["claims"]) + "</ul>")
    parts.append(f"<p>For agents: <a href='/case/{esc(cid)}.md'>this case as Markdown</a> · "
                 f"<a href='/data/cases/{esc(cid)}.json'>all the data as JSON</a> · <a href='/llms.txt'>llms.txt</a></p>")
    return "\n".join(parts)


def prerender_list(title: str, lede: str, items: list) -> str:
    return (f"<h1>{esc(title)}</h1><p>{esc(lede)}</p><ul>"
            + "".join(f"<li><a href='{esc(u)}'>{esc(t)}</a>{(' — ' + esc(d)) if d else ''}</li>" for u, t, d in items)
            + "</ul><p>For agents: <a href='/llms.txt'>llms.txt</a></p>")


def page(template: str, *, path: str, title: str, desc: str, image: str, body: str, md: str | None = None,
         noindex: bool = False) -> str:
    url = SITE_URL + (path if path != "/" else "/")
    img = f"{SITE_URL}/{image}"
    t = template
    t = t.replace('<html lang="en">', '<html lang="en" data-router="path">', 1)
    t = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>", t, count=1, flags=re.S)
    for prop, val in [("description", desc), ("twitter:title", title), ("twitter:description", desc)]:
        t = re.sub(rf'(<meta name="{re.escape(prop)}" content=")[^"]*(")', lambda m, val=val: m.group(1) + esc(val) + m.group(2), t)
    for prop, val in [("og:title", title), ("og:description", desc), ("og:image", img)]:
        t = re.sub(rf'(<meta property="{re.escape(prop)}" content=")[^"]*(")', lambda m, val=val: m.group(1) + esc(val) + m.group(2), t)
    extra = [f'<link rel="canonical" href="{esc(url)}">', f'<meta property="og:url" content="{esc(url)}">',
             f'<meta name="twitter:image" content="{esc(img)}">',
             '<link rel="alternate" type="text/plain" title="For AI agents" href="/llms.txt">',
             '<link rel="alternate" type="text/calendar" title="The Docket" href="/docket.ics">']
    if md:
        extra.append(f'<link rel="alternate" type="text/markdown" href="{esc(md)}">')
    if noindex:
        extra.append('<meta name="robots" content="noindex">')
    t = t.replace('<link rel="icon"', "\n  ".join(extra) + '\n  <link rel="icon"', 1)
    # assets: root-absolute, since pages now live at /case/OS-0014 etc.
    t = t.replace('href="favicon.svg"', 'href="/favicon.svg"').replace('href="css/', 'href="/css/').replace('src="js/', 'src="/js/')
    t = re.sub(r'(<main id="app"[^>]*>).*?(</main>)',
               lambda m: f'{m.group(1)}\n    <p class="loading">Pointing the telescope…</p>\n    <div class="prerender">{body}</div>\n  {m.group(2)}',
               t, count=1, flags=re.S)
    return t


def build(out: Path = DIST) -> None:
    index, cases = load_cases()
    hunts, wrong = load_hunts()
    docket = build_docket(index, cases)
    template = (WEB / "index.html").read_text()

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB, out, ignore=shutil.ignore_patterns("dev", "README.md", ".DS_Store"))

    write(out / "data" / "hunts.json", json.dumps({"hunts": hunts, "wrong": wrong}, ensure_ascii=False, indent=1))
    write(out / "data" / "docket.json", json.dumps({"built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                    "items": docket}, ensure_ascii=False, indent=1))
    write(out / "docket.ics", build_ics(docket))
    write(out / "data" / "sky" / "cases.json", json.dumps(sky_cases(index, cases), separators=(",", ":")))
    write(out / "llms.txt", llms_txt(index, cases, hunts, docket))

    def og(name):
        return f"og/{name}.png" if (WEB / "og" / f"{name}.png").exists() else "og.png"

    meta = {c["id"]: c for c in index.get("cases", [])}
    pending = [d for d in docket if d["outcome"] == "pending"]
    routes = []

    home_desc = ("The sky has been recorded; almost none of it has been looked at. Oddsky is an open observatory where you and "
                 "your AI agent investigate strange stars in real telescope data, and the sky grades every prediction.")
    routes.append(("/", "Oddsky — an open observatory your AI agent can use", home_desc, og("home"), prerender_list(
        "Oddsky", TAGLINE + " " + DEFAULT_DESC,
        [(f"/case/{c['id']}", f"{c['id']}: {c.get('title')}", clip(c.get("hook") or "", 140)) for c in index["cases"] if c["id"] in cases]), None))
    routes.append(("/cases", "Cases — Oddsky", "Each case is one strange star: its data from every archive that has seen it, and an open argument about what it is.",
                   og("home"), prerender_list("Cases", "The casebook.", [(f"/case/{c['id']}", f"{c['id']}: {c.get('title')}", c.get("target")) for c in index["cases"] if c["id"] in cases]), None))
    for cid, payload in cases.items():
        c = payload.get("case", {})
        md = f"/case/{cid}.md"
        write(out / "case" / f"{cid}.md", case_markdown(cid, payload, meta.get(cid, {})))
        routes.append((f"/case/{cid}", f"{c.get('title') or cid} — {cid} — Oddsky", clip(c.get("hook") or c.get("summary") or DEFAULT_DESC, 220),
                       og(cid), prerender_case(cid, payload), md))
    routes.append(("/hunts", "Hunts — Oddsky", "Sky-wide searches: 176.9 million stars in, a handful out, and every step of the funnel published, including what we got wrong.",
                   og("home"), prerender_list("Hunts", "Sky-wide searches.", [(f"/hunt/{x['id']}", f"{x['id']}: {x['title']}", x["verdict"]) for x in hunts]), None))
    for hu in hunts:
        md = None
        if hu.get("readme"):
            md = f"/hunt/{hu['id']}.md"
            write(out / "hunt" / f"{hu['id']}.md", hu["readme"])
        routes.append((f"/hunt/{hu['id']}", f"{hu['title']} — {hu['id']} — Oddsky", clip(hu["question"] + " " + hu["verdict"], 220),
                       og(hu["cases"][0]) if hu["cases"] and hu["cases"][0] in cases else og("home"),
                       prerender_list(hu["title"], hu["question"], [(f"/case/{x}", x, None) for x in hu["cases"] if x in cases]), md))
    routes.append(("/docket", "The Docket — Oddsky",
                   f"{len(pending)} sealed predictions waiting for the sky, each with a probability and a date. Subscribe and your calendar tells you when the universe grades us.",
                   og("home"), prerender_list("The Docket", "Every sealed prediction, and the day the sky answers it.",
                                              [(d["href"], f"{d.get('case') or d.get('packet')} {d['id']} ({pct(d['probability'])}, {d['outcome']}, {d.get('resolve_by') or ''})", d["statement"]) for d in docket]), None))
    routes.append(("/trials", "Trials — Oddsky", "Strange Stars Trial 001: blind and hindsight trials of AI investigators, answers sealed by hash before anyone ran.",
                   og("home"), prerender_list("Trials", "Blind and hindsight trials with sealed answers.", []), None))
    routes.append(("/agents", "For agents — Oddsky", "Point any AI agent at Oddsky: a zero-install path through llms.txt and per-case dossiers, and an MCP server for the full observatory.",
                   og("home"), prerender_list("For agents", "Start at /llms.txt.", [("/llms.txt", "llms.txt", None)]), "/llms.txt"))
    routes.append(("/observe", "Get your observer code — Oddsky", "An observer code like AAVSO's, secured by a passkey. Then your agent gets the whole observatory in one line, and everything it finds is credited to you.",
                   og("home"), prerender_list("Observe", "Get your observer code.", []), None))
    routes.append(("/ledger", "The Sky Ledger — Oddsky", "Every prediction sealed on Oddsky and every grade the sky has given, in one hash-chained log anyone can re-verify in their browser.",
                   og("home"), prerender_list("The Sky Ledger", "An append-only, hash-chained log of sealed predictions.", [("/api/ledger?format=jsonl", "the ledger as JSONL", None)]), None))
    routes.append(("/app", "Oddsky", DEFAULT_DESC, og("home"), "", None))
    routes.append(("/privacy", "Privacy — Oddsky", "What Oddsky keeps about observers, and why.", og("home"),
                   "<h1>Privacy</h1><p>Oddsky keeps your observer code, chosen name, the provider ID and username/email of any linked GitHub or Google account, passkey public keys, and hashes of session tokens and keys. No ads, no tracking. Contact alan@tangohq.com.</p>", None))
    routes.append(("/terms", "Terms — Oddsky", "The terms of using Oddsky.", og("home"),
                   "<h1>Terms</h1><p>Oddsky is free and offered as is. Published notebooks and sealed predictions are public; sealed predictions cannot be withdrawn. Contact alan@tangohq.com.</p>", None))
    routes.append(("/about", "About — Oddsky", DEFAULT_DESC, og("home"), prerender_list("About", DEFAULT_DESC, []), None))

    for path, title, desc, image, body, md in routes:
        dest = out / ("index.html" if path == "/" else f"{path.lstrip('/')}.html")
        write(dest, page(template, path=path, title=title, desc=desc, image=image, body=body, md=md))
    write(out / "404.html", page(template, path="/404", title="Nothing at these coordinates — Oddsky", desc=DEFAULT_DESC,
                                 image="og.png", body="<h1>Nothing at these coordinates.</h1><p><a href='/cases'>Browse the cases</a>.</p>", noindex=True))

    today = date.today().isoformat()
    write(out / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{esc(SITE_URL + (p if p != '/' else '/'))}</loc><lastmod>{today}</lastmod></url>\n" for p, *_ in routes)
          + "</urlset>\n")
    write(out / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(f"built {out.relative_to(ROOT)}/: {len(routes)} pages, {len(cases)} case dossiers, {len(hunts)} hunts, "
          f"{len(docket)} predictions ({len(pending)} sealed)")


# ---- local preview with clean URLs ---------------------------------------------------------------

def serve(port: int) -> None:
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    api = os.environ.get("ODDSKY_API")  # e.g. http://localhost:8081: proxy /api and /mcp there, as vercel.json does

    class Clean(SimpleHTTPRequestHandler):
        def _proxy(self):
            import urllib.error
            import urllib.request

            n = int(self.headers.get("content-length") or 0)
            req = urllib.request.Request(api + self.path, data=self.rfile.read(n) if n else None, method=self.command,
                                         headers={k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")})
            try:
                r = urllib.request.urlopen(req, timeout=300)
            except urllib.error.HTTPError as e:
                r = e
            body = r.read()
            self.send_response(r.status if hasattr(r, "status") else r.code)
            for k, v in r.headers.items():
                if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if api and (self.path.startswith("/api/") or self.path.startswith("/mcp")):
                return self._proxy()
            return super().do_GET()

        def do_POST(self):
            if api and (self.path.startswith("/api/") or self.path.startswith("/mcp")):
                return self._proxy()
            self.send_error(405)

        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".md": "text/markdown; charset=utf-8",
                          ".txt": "text/plain; charset=utf-8", ".ics": "text/calendar; charset=utf-8", ".js": "text/javascript"}

        def send_head(self):
            p = self.path.split("?", 1)[0].split("#", 1)[0]
            if re.match(r"^/(n|o)/[^/]+$", p):  # vercel.json rewrites these to the app shell
                p = self.path = "/app"
            f = DIST / p.lstrip("/")
            if p != "/" and not f.exists() and (DIST / (p.lstrip("/") + ".html")).exists():
                self.path = p + ".html"
            elif p != "/" and not f.exists():
                self.send_response(404)
                body = (DIST / "404.html").read_bytes()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return None
            return super().send_head()

    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(Clean, directory=str(DIST)))
    print(f"serving http://localhost:{port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    build()
    if a.serve:
        serve(a.port)
    sys.exit(0)
