"""The `oddsky` command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False,
                  help="Oddsky: an open observatory your AI agent can use. The universe is an open question.")
trial_app = typer.Typer(no_args_is_help=True, help="Blind and hindsight trials: can an investigator recover the truth?")
app.add_typer(trial_app, name="trial")


def _echo(obj) -> None:
    from .case.store import _jsonable

    typer.echo(json.dumps(obj, indent=2, default=_jsonable))


@app.command("open")
def open_cmd(name: str, title: Annotated[str | None, typer.Option()] = None,
             hook: Annotated[str, typer.Option()] = "", fetch: bool = True,
             surveys: Annotated[str, typer.Option(help="comma list")] = "gaia,neowise,aavso,ztf,atlas,asassn,tess,librarian"):
    """Open a case on a real star by name and fetch its data."""
    from .fetch import fetch as do_fetch
    from .fetch import open_case

    s = open_case(name, title, hook)
    typer.echo(f"{s.path.name}: {s.load().title}")
    if fetch:
        _echo(do_fetch(s, surveys.split(",")))


@app.command("fetch")
def fetch_cmd(case: str, surveys: Annotated[str, typer.Option()] = "gaia,neowise,aavso,ztf,atlas,asassn,tess,librarian"):
    """(Re)fetch archive data for a case."""
    from .case.store import CaseStore
    from .fetch import fetch

    _echo(fetch(CaseStore.find(case), surveys.split(",")))


@app.command("skeptic")
def skeptic_cmd(case: str):
    """Run the Skeptic's artifact battery on a case."""
    from . import skeptic
    from .case.store import CaseStore

    r = skeptic.run(CaseStore.find(case))
    mark = {"pass": "✓", "warn": "!", "fail": "✗", "skip": "–"}
    for c in r["checks"]:
        typer.echo(f" {mark[c['status']]} {c['title']}\n     {c['finding']}")
    typer.echo(f"\n{r['summary']}")


# ignore_unknown_options: a negative declination (-42.8842) is an argument, not an option
@app.command("librarian", context_settings={"ignore_unknown_options": True})
def librarian_cmd(ra: Annotated[float, typer.Argument(help="degrees")], dec: Annotated[float, typer.Argument(help="degrees")],
                  radius: Annotated[float, typer.Option(help="arcsec")] = 5.0,
                  topic: Annotated[list[str] | None, typer.Option(help="repeatable; default: every topic")] = None,
                  epoch: Annotated[float | None, typer.Option(help="date of the position as a decimal year (2010.5 for "
                                                              "AllWISE): SIMBAD's stars are moved to it by their proper "
                                                              "motion; default: no motion")] = None):
    """Ask the Librarian whether a sky position is new: SIMBAD, NED, ADS, the big catalogues and the shelves of published
    samples. Verdicts: unlisted | catalogued (an object, nothing on the topics: not proof that nothing is published) |
    mentioned (topical titles only in papers that list more than 500 objects) | studied (read those first)."""
    from .librarian import ABOUT_MAX_OBJECTS, TOPICS, prior_art

    unknown = [t for t in topic or [] if t not in TOPICS]
    if unknown:
        typer.echo(f"unknown topic(s) {unknown}; topics are {list(TOPICS)}", err=True)
        raise typer.Exit(2)
    r = prior_art(ra, dec, radius, topic, epoch=epoch)
    typer.echo(r["summary"])
    sim, ned, src = r["simbad"], r["ned"], r["sources"]
    if sim:
        near = sim["nearest"]
        typer.echo(f"  SIMBAD: {sim['main_id']} ({sim['otype']}), {sim['sep_arcsec']:.1f}\" away"
                   + (f" at {epoch:g}" if epoch is not None else "")
                   + (f"; {sim['n_objects']} objects in the cone, this one has the most references ({sim['n_refs']}); the nearest "
                      f"is {near['main_id']} ({near['otype']}) at {near['sep_arcsec']:.1f}\"" if near["main_id"] != sim["main_id"]
                      else f"; {sim['n_objects']} objects in the cone" if sim["n_objects"] > 1 else ""))
    else:
        typer.echo(f"  SIMBAD: no object [{src['simbad']['status']}]")
    if ned:
        typer.echo(f"  NED:    {ned['prefname']} ({ned['type'] or 'no type'}" + (f", z = {ned['z']:.4f}" if ned["z"] is not None else "")
                   + f"), {ned['sep_arcsec']:.1f}\" away" + (f"; {ned['n_objects']} objects in the cone" if ned["n_objects"] > 1 else ""))
    else:
        typer.echo(f"  NED:    no object [{src['ned']['status']}]")
    if r["nearby"]:
        typer.echo(f"  nearest object outside the radius: {r['nearby']['name']} ({r['nearby']['source']}"
                   + (f", {r['nearby']['type']}" if r["nearby"]["type"] else "") + f"), {r['nearby']['sep_arcsec']:.1f}\" away")
    ads = src["ads"]
    asked = ", ".join(ads.get("asked") or [])
    typer.echo("  ADS:    " + {"ok": f"asked about {asked}", "empty": f"no paper on {asked}",
                               "unresolved": f"did not recognise {asked}: not an answer",
                               "not_asked": "not asked (no object name to look up)",
                               "unavailable": "could not be queried"}.get(ads["status"], ads["status"]))
    for note in ads["notes"] if ads["status"] != "not_asked" else []:
        typer.echo(f"          {note}")
    for o in r["otype_hits"]:
        typer.echo(f"  SIMBAD type: {o['main_id']} is a {o['label']} ({o['otype']}), {o['sep_arcsec']:.1f}\" away")
    for c in r["catalogues"]:
        if c["status"] == "ok":
            h = c["hits"][0]
            what = "published as variable" if c["kind"] == "variable" else "listed as an AGN or AGN candidate; does not change the verdict"
            typer.echo(f"  {c['name']}: {h['object']}" + (f" (type {h['class']})" if h.get("class") else "")
                       + (f", {h['sep_arcsec']:.1f}\" away" if h.get("sep_arcsec") is not None else "") + f", {c['bibcode']} [{what}]")
        elif c["status"] == "unavailable":
            typer.echo(f"  {c['name']} could not be queried: {'; '.join(c['notes']) or 'no reason given'}")
    quiet = [c["name"] for c in r["catalogues"] if c["status"] == "empty"]
    if quiet:
        typer.echo(f"  no entry in: {', '.join(quiet)}")
    for k in ("simbad", "ned", "ads"):
        if src[k]["status"] == "unavailable":
            typer.echo(f"  {k} could not be queried: {'; '.join(src[k]['notes']) or 'no reason given'}")
    for h in r["shelf_hits"]:
        typer.echo(f"  shelf {h['shelf']}: {h['name']} at {h['sep_arcsec']:.1f}\", {h['bibcode']} {h['title']}")
    lists = r["n_topical"] - r["n_about"]
    typer.echo(f"  {r['n_papers']} paper(s), {r['n_topical']} on the topics ({', '.join(r['topics'])})"
               + (f", {lists} of them in lists of more than {ABOUT_MAX_OBJECTS} objects" if lists else "")
               + (", newest first:" if r["topical_papers"] else ""))
    for p in r["topical_papers"][:10]:
        typer.echo(f"    {p['bibcode']}  {p['year'] or '----'}  {p['title']}"
                   + (f"  [a list of {p['n_objects']} objects]" if p["big_list"] else ""))
    if r["n_topical"] > 10:
        typer.echo(f"    ... and {r['n_topical'] - 10} more")


@app.command("tools")
def tools_cmd(blind: bool = False, verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False):
    """List the investigation tools with their arguments (the same ones the MCP server exposes)."""
    import inspect

    from .tools import Toolbox, available

    tb = Toolbox()
    for name in available("blind" if blind else "open"):
        fn = getattr(tb, name)
        params = []
        for p in inspect.signature(fn).parameters.values():
            params.append(p.name if p.default is inspect.Parameter.empty else f"{p.name}={p.default!r}")
        doc = inspect.getdoc(fn) or ""
        typer.echo(f"{name}({', '.join(params)})")
        typer.echo("    " + (doc.replace("\n", "\n    ") if verbose else doc.split("\n")[0]))


@app.command("call")
def call_cmd(tool: str, args: Annotated[str, typer.Argument(help="JSON object of arguments")] = "{}",
             blind: Annotated[Path | None, typer.Option(help="trial packet directory")] = None,
             author: Annotated[str | None, typer.Option()] = None):
    """Call one tool exactly as an MCP client would: `oddsky call describe_series '{"case":"OS-0001","series":"NEOWISE:W1"}'`."""
    from .tools import Toolbox, available

    mode = "blind" if blind else "open"
    if tool not in available(mode):
        typer.echo(f"unknown or unavailable tool in {mode} mode: {tool}", err=True)
        raise typer.Exit(2)
    tb = Toolbox(mode=mode, blind_root=blind, author=author)
    try:
        _echo(getattr(tb, tool)(**json.loads(args)))
    except Exception as e:  # noqa: BLE001
        _echo({"error": f"{type(e).__name__}: {e}"})
        raise typer.Exit(1) from None


@app.command("mcp")
def mcp_cmd(blind: Annotated[Path | None, typer.Option(help="serve one blind trial packet")] = None,
            author: Annotated[str | None, typer.Option()] = None):
    """Serve the toolbox over MCP (stdio)."""
    from .mcp_server import serve

    serve("blind" if blind else "open", blind, author)


@app.command("replay")
def replay_cmd(case: str, strict: bool = False, seal: bool = False):
    """Re-run every analysis call in a case's ledger and check the results still match their digests.
    Calls recorded with an older oddsky version that no longer match are reported as drift; they
    fail only with --strict (replay them exactly by checking out that version)."""
    from .replay import replay

    res = replay(case, seal=seal)
    for r in res:
        mark = "✓" if r["match"] else ("~" if r["drift"] or r["platform_drift"] else "✗")
        typer.echo(f" {mark} {r['id']} {r['tool']} {r.get('note', '')}")
    bad = sum(not r["match"] and not r["drift"] and not r["platform_drift"] for r in res)
    drift = sum(r["drift"] for r in res)
    pdrift = sum(r["platform_drift"] for r in res)
    typer.echo(f"{len(res) - bad - drift - pdrift}/{len(res)} reproduced, {drift} drifted across versions, "
               f"{pdrift} differ only across platforms, {bad} failed")
    if bad or (strict and drift):
        raise typer.Exit(1)


@app.command("check")
def check_cmd(case: str):
    """Grade every machine-checkable prediction in a case against current data."""
    from .tools import Toolbox

    tb = Toolbox(author="oddsky-check")
    c = tb.store(case).load()
    for p in c.predictions:
        if p.check:
            r = tb.check_prediction(case, p.id)
            typer.echo(f"{p.id} [{r['outcome']}] p={p.probability:.2f} {p.statement}  ({r['note']})")


@app.command("paper-check")
def paper_check_cmd(claims: Path, final: bool = False):
    """Recompute every number in a document from the data (the claims file next to it declares how) and fail on
    a wrong value, an exception to a universal statement, or a numeral nobody declared. --final also requires a
    referee review of exactly this text."""
    from .paper import run

    r = run(claims, final=final)
    for f in r["failures"]:
        typer.echo(" ✗ " + f)
    for text, source in r["external"]:
        typer.echo(f" ~ external, not recomputed: {text!r}  ({source})")
    typer.echo(f"{r['checked']} statements recomputed, {len(r['external'])} external, {len(r['failures'])} failures; "
               f"reviewed: {r['reviewed']}; sha256 {r['sha256']}")
    if not r["ok"]:
        raise typer.Exit(1)


@app.command("export-web")
def export_cmd(out: Annotated[Path | None, typer.Option()] = None):
    """Write web/data/*.json for the static viewer."""
    from .export import export_web

    typer.echo("exported: " + ", ".join(export_web(out)))


@trial_app.command("build")
def trial_build(spec: Path):
    """Build blind/hindsight packets from a trial spec (trials/<name>/spec.yaml) and seal the answers."""
    from .trials.build import build

    _echo(build(spec))


@trial_app.command("score")
def trial_score(trial: Path, agent: Annotated[str, typer.Option()],
                answers: Annotated[Path | None, typer.Option()] = None):
    """Score an agent's hypotheses and predictions against the (revealed) answers."""
    from .trials.score import score

    _echo(score(trial, agent, answers)["summary"])


@trial_app.command("verify")
def trial_verify(trial: Path):
    """Check that a revealed answer file matches the commitment sealed before the trial ran."""
    from .trials.seal import verify

    ok = verify(trial)
    typer.echo("sealed answers verified ✓" if ok else "MISMATCH: answers differ from the sealed commitment ✗")
    if not ok:
        raise typer.Exit(1)


def main():  # pragma: no cover
    sys.exit(app())


if __name__ == "__main__":
    main()
