"""Build the review kit that goes with a brief: one folder per case, everything a reviewer needs offline.

    python scripts/build_review_kit.py <out.zip> <date> OS-0014 OS-0015 OS-0013

Per case: case.yaml, ledger.jsonl, provenance.yaml, context.json, the referee report(s) (referee.md, or
referee-<n>.md when there are several), figures, external/ (data pulled outside the toolkit, including archived
referee inputs) and lightcurves/*.csv (every data/*.parquet as CSV: t_mjd, mag, err, band, survey, flag; flag empty
= good, `upper_limit` = limit at the quoted magnitude).
"""
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKY = ("Sky cutouts (Aladin Lite, any survey)", "https://aladin.cds.unistra.fr/AladinLite/?target={ra:.6f}%20{dec:.6f}&fov=0.03")
SIMBAD = ("SIMBAD", "https://simbad.cds.unistra.fr/simbad/sim-coo?Coord={ra:.6f}{dec:+.6f}&Radius=10&Radius.unit=arcsec")
VIZIER = ("VizieR photometry at this position", "https://vizier.cds.unistra.fr/viz-bin/sed?-c={ra:.6f}{dec:+.6f}&-c.rs=3")


def build_case(cid: str, out: Path) -> dict:
    src = ROOT / "cases" / cid
    dst = out / cid
    (dst / "lightcurves").mkdir(parents=True)
    shutil.copy(src / "case.yaml", dst / "case.yaml")
    shutil.copy(src / "ledger.jsonl", dst / "ledger.jsonl")
    for name in ("provenance.yaml", "context.json"):
        if (src / "data" / name).exists():
            shutil.copy(src / "data" / name, dst / name)
    reviews = sorted((src / "reviews").glob("*.md"))
    for i, r in enumerate(reviews, 1):
        shutil.copy(r, dst / ("referee.md" if len(reviews) == 1 else f"referee-{i}-{r.stem}.md"))
    for fig in sorted((src / "figures").glob("*.png")):
        shutil.copy(fig, dst / fig.name)
    if (src / "data" / "external").is_dir():
        shutil.copytree(src / "data" / "external", dst / "external")
    lcs = []
    for pq in sorted((src / "data").glob("*.parquet")):
        pd.read_parquet(pq).to_csv(dst / "lightcurves" / f"{pq.stem}.csv", index=False)
        lcs.append(f"{pq.stem}.csv")
    case = yaml.safe_load((src / "case.yaml").read_text())
    return {"id": cid, "title": case["title"], "status": case.get("status"), "name": case["target"]["name"],
            "ra": float(case["target"]["ra"]), "dec": float(case["target"]["dec"]), "lcs": lcs}


def main() -> None:
    out_zip, date, cases = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
    with tempfile.TemporaryDirectory() as tmp:
        kit = Path(tmp) / "oddsky_review_kit"
        kit.mkdir()
        info = [build_case(c, kit) for c in cases]
        lines = [f"# Oddsky review kit ({date})", "",
                 "One folder per case. `lightcurves/*.csv` are the full time series as used (columns: t_mjd, mag, err, "
                 "band, survey, flag; flag empty = good, `upper_limit` = limit at the quoted magnitude). `context.json` "
                 "holds the Gaia DR3 context and neighbours; `provenance.yaml` records every archive query and cut; "
                 "`referee.md` is the adversarial report; `external/` holds data pulled outside the toolkit, including "
                 "the referee's own inputs where they ran outside it. `case.yaml` carries every claim, including errata, "
                 "which are appended rather than edited in place. Case pages with the same material rendered: "
                 "https://oddsky.ai/case/<id>.", ""]
        for c in info:
            lines += [f"## {c['id']}: {c['title']}", "",
                      f"Target: {c['name']} at RA {c['ra']:.6f}, Dec {c['dec']:.6f} (J2000). Status on the Oddsky "
                      f"ladder: {c['status']}.", "", f"- Case page: https://oddsky.ai/case/{c['id']}"]
            lines += [f"- {label}: {url.format(ra=c['ra'], dec=c['dec'])}" for label, url in (SKY, SIMBAD, VIZIER)]
            lines += [f"- Light curves here: {', '.join(c['lcs'])}", ""]
        (kit / "README.md").write_text("\n".join(lines))
        out_zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(kit.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(kit.parent))
    print("wrote", out_zip)


if __name__ == "__main__":
    main()
