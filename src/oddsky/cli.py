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
             surveys: Annotated[str, typer.Option(help="comma list")] = "gaia,neowise,aavso,ztf,atlas,asassn,tess"):
    """Open a case on a real star by name and fetch its data."""
    from .fetch import fetch as do_fetch
    from .fetch import open_case

    s = open_case(name, title, hook)
    typer.echo(f"{s.path.name}: {s.load().title}")
    if fetch:
        _echo(do_fetch(s, surveys.split(",")))


@app.command("fetch")
def fetch_cmd(case: str, surveys: Annotated[str, typer.Option()] = "gaia,neowise,aavso,ztf,atlas,asassn,tess"):
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
def replay_cmd(case: str, strict: bool = False):
    """Re-run every analysis call in a case's ledger and check the results still match their digests.
    Calls recorded with an older oddsky version that no longer match are reported as drift; they
    fail only with --strict (replay them exactly by checking out that version)."""
    from .replay import replay

    res = replay(case)
    for r in res:
        mark = "✓" if r["match"] else ("~" if r["drift"] else "✗")
        typer.echo(f" {mark} {r['id']} {r['tool']} {r.get('note', '')}")
    bad = sum(not r["match"] and not r["drift"] for r in res)
    drift = sum(r["drift"] for r in res)
    typer.echo(f"{len(res) - bad - drift}/{len(res)} reproduced, {drift} drifted across versions, {bad} failed")
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
