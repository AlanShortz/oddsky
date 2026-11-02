"""Gaia DR4 day, one command (hunt H-0014).

    uv run python scripts/dr4_day.py --release dr4                 # release day: every stage, tier 1 then tier 2
    uv run python scripts/dr4_day.py --release dr3                 # dry run against Gaia DR3, the stand-in release
    uv run python scripts/dr4_day.py --release dr4 --stages probe  # one stage (probe, readiness, idmap, ensemble,
                                                                    # catalogue, epochs, search, report)
    uv run python scripts/dr4_day.py --release dr4 --tiers 1       # tier 1 only (the first hour)
    uv run python scripts/dr4_day.py --release dr4 --set tables.vari_microlensing=gaiadr4.vari_microlensing_x

Outputs go to ~/oddsky-runs/h0014/<release>/ (summary.md first); small tables are copied into hunts/H-0014/. Stages are
resumable: epoch photometry is cached per source, and re-running a stage overwrites only its own outputs. Nothing is
written to a case, the Sky Ledger or a sealed prediction (the DR4 ensemble id map is the one documented exception,
dr4_ensemble.md 2.5 item 4, written only for the real release and never overwritten). Exit status 1 if the probe or
readiness stage says the release is not being served as configured.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from oddsky.dr4day import config, pipeline


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--release", default=None, help="dr4 or dr3 (default: $ODDSKY_GAIA_RELEASE, else dr3)")
    ap.add_argument("--stages", default=",".join(pipeline.STAGES))
    ap.add_argument("--tiers", default="1,2")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a release setting")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    rel = config.release(a.release, config.parse_overrides(a.set))
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    bad = [s for s in stages if s not in pipeline.STAGES]
    if bad:
        ap.error(f"unknown stages {bad}; choose from {pipeline.STAGES}")
    if not Path("cases").is_dir():
        ap.error("run from the repo root")
    st = pipeline.run(rel, stages=stages, tiers=tuple(int(x) for x in a.tiers.split(",")))
    def word(k, v):
        if not v.get("ok"):
            return "FAILED"
        if k == "probe" and not v.get("probe_ok"):
            return "ran; release NOT served as configured"
        if k == "readiness" and v.get("release_failed"):
            return "ran; release request FAILED"
        return "ok"
    print(f"\n{rel.name}: " + ", ".join(f"{k} {word(k, v)}" for k, v in st.items() if k in stages))
    print(f"summary: {config.run_dir(rel) / 'summary.md'}")
    if "probe" in st and st["probe"].get("fixes"):
        print("probe fixes:\n  " + "\n  ".join(st["probe"]["fixes"]))
    bad_probe = "probe" in stages and not (st["probe"].get("ok") and st["probe"].get("probe_ok"))
    bad_ready = "readiness" in stages and st.get("readiness", {}).get("release_failed")
    return 1 if bad_probe or bad_ready else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
