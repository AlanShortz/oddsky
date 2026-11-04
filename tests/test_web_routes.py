"""The site's in-page router must only claim paths it renders. Anything else is the server's and needs a
real page load: when the router swallowed /api/oauth/<provider>/start, "Continue with GitHub/Google"
did nothing (2026-11-03). Every path vercel.json proxies to the hosted service must stay unclaimed."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
node = shutil.which("node")
pytestmark = pytest.mark.skipif(not node, reason="node not installed")


def routes(paths):
    script = ("import(process.argv[1]).then(({ parseRoute }) => console.log(JSON.stringify("
              "JSON.parse(process.argv[2]).map((p) => parseRoute(p).name))));")
    out = subprocess.run([node, "--input-type=module", "-e", script, (ROOT / "web/js/routes.js").as_uri(), json.dumps(paths)],
                         capture_output=True, text=True, check=True).stdout
    return dict(zip(paths, json.loads(out), strict=True))


def server_paths():
    """Concrete sample paths for each vercel.json rewrite to the hosted service."""
    rewrites = json.loads((ROOT / "vercel.json").read_text())["rewrites"]
    return [r["source"].replace(":path*", "x/y").replace(":id", "x") for r in rewrites if r["destination"].startswith("https://")]


def test_server_paths_are_not_routed_in_page():
    paths = server_paths() + ["/api/oauth/github/start?next=%2Fobserve", "/api/oauth/google/start", "/api/ledger?format=jsonl"]
    assert "/api/x/y" in paths and "/mcp" in paths
    claimed = {p: name for p, name in routes(paths).items() if name != "notfound"}
    assert not claimed, f"the in-page router would swallow these server paths: {claimed}"


def test_site_pages_are_still_routed():
    got = routes(["/", "/index.html", "/case/OS-0001", "/hunt/H-0016", "/observe", "/ledger", "/n/abc", "/o/ash", "cases"])
    assert got == {"/": "home", "/index.html": "home", "/case/OS-0001": "case", "/hunt/H-0016": "hunt", "/observe": "observe",
                   "/ledger": "ledger", "/n/abc": "notebook", "/o/ash": "observer", "cases": "cases"}


def test_link_interceptor_defers_to_the_router():
    """main.js's click handler is what swallowed the OAuth links: it must let unrouted paths load for real."""
    main = (ROOT / "web/js/main.js").read_text()
    handler = main[main.index("function setupLinks"):main.index("e.preventDefault()", main.index("function setupLinks"))]
    assert "parseRoute(url.pathname).name === 'notfound') return" in handler
