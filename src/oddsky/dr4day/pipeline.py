"""The DR4-day pipeline: stages, in order, each writing to ~/oddsky-runs/h0014/<release>/ and never to a case or the ledger.

  probe       what the archive serves (tables, columns, DataLink products, epoch layout); fixes listed     ~2 min
  readiness   sealed GAIA predictions: release, span, coverage, identity, provisional grade                ~1 min
  idmap       DR3 -> release ids for every target (neighbourhood table)                                     ~2 min
  ensemble    the sealed H-0009 ensemble grader, unchanged (subprocess), plus its DR3 self-test             ~3 min
  catalogue   release lens catalogue, classifier-only lenses, flags/classes of our targets, cones, xmatch   ~5 min
  epochs      epoch photometry for every target (tier 1 first), cached per source                          tier 1 ~5 min
  search      blind light-curve analysis of every target, ranked; quick-look plots of the top               ~10 min
  report      summary.md + small tables copied into hunts/H-0014/<release>/

Timings are for the DR3 dry run (anonymous, 50 ids per DataLink request); DR4 day will be slower while the archive is busy.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import catalogue, lightcurves, probe, readiness, targets
from .archive import Archive
from .config import Release, run_dir

log = logging.getLogger("oddsky.dr4day")
STAGES = ("probe", "readiness", "idmap", "ensemble", "catalogue", "epochs", "search", "report")
ENSEMBLE_DIR = Path("hunts/H-0009/predictions")
HUNT = Path("hunts/H-0014")


class Run:
    def __init__(self, rel: Release, tiers=(1, 2), root: Path = Path("."), archive: Archive | None = None,
                 out: Path | None = None):
        self.rel, self.tiers, self.root = rel, tuple(tiers), root
        self.out = out or run_dir(rel)
        self.arc = archive or Archive(rel)
        self.status: dict = {}
        p = self.out / "status.json"
        if p.exists():
            self.status = json.loads(p.read_text())

    # ---- helpers ----
    def path(self, name: str) -> Path:
        p = self.out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def save_status(self):
        self.path("status.json").write_text(json.dumps(self.status, indent=1, default=str))
        if self.arc.errors:
            with open(self.path("errors.jsonl"), "w") as f:
                for e in self.arc.errors:
                    f.write(json.dumps(e, default=str) + "\n")

    def stage(self, name: str):
        t0 = time.time()
        log.info("== stage %s (%s)", name, self.rel.name)
        try:
            info = getattr(self, f"do_{name}")() or {}
            self.status[name] = {"ok": True, "seconds": round(time.time() - t0, 1), **info}
        except Exception as e:  # noqa: BLE001  a failed stage is recorded and the next stages still run
            log.exception("stage %s failed", name)
            self.status[name] = {"ok": False, "seconds": round(time.time() - t0, 1), "error": f"{type(e).__name__}: {e}"[:500]}
        self.status[name]["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save_status()
        return self.status[name]

    def targets(self) -> pd.DataFrame:
        p = self.path("targets.csv")
        if not p.exists():
            targets.build(self.root, self.tiers).to_csv(p, index=False)
        t = pd.read_csv(p, dtype={"source_id": str})
        t["source_id"] = t.source_id.fillna("")
        return t[t.tier.isin(self.tiers)]

    def idm(self) -> pd.DataFrame | None:
        """The DR3 -> release id map, applied to every later stage. The stand-in's map is DR2 -> DR3 asked with DR3 ids,
        which exercises the code but is not a valid map (two of our DR3 ids are also DR2 ids of other stars), so a dry run
        records it and does not apply it."""
        if self.rel.stand_in:
            return None
        p = self.out / "idmap.csv"
        return pd.read_csv(p, dtype={"dr3_source_id": str, "new_source_id": str}) if p.exists() else None

    # ---- stages ----
    def do_probe(self):
        r = probe.run(self.arc, self.rel)
        self.path("probe.json").write_text(json.dumps(r, indent=1, default=str))
        return {"probe_ok": r["ok"], "fixes": r["fixes"], "epoch_layout": r.get("epoch", {}).get("layout"),
                "retrieval_types": r.get("datalink", {}).get("retrieval_types")}

    def do_readiness(self):
        rows, failed = readiness.check(self.rel, root=self.root)
        with open(self.path("readiness.jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r, default=str) + "\n")
        s = readiness.summary(rows, failed, self.rel)
        self.path("readiness.txt").write_text(s + "\n")
        return {"summary": s, "release_failed": failed}

    def do_idmap(self):
        ids = targets.unique_ids(self.targets())
        m = catalogue.idmap(self.arc, self.rel, ids)
        m.to_csv(self.path("idmap.csv"), index=False)
        changed = int((m.new_source_id != m.dr3_source_id).sum())
        info = {"n": len(m), "changed": changed, "unmatched": int(m.rule.str.startswith("no").sum())}
        # The ensemble's id map (dr4_ensemble.md 2.5 item 4) is written only for the real release, and never overwritten.
        ens = ENSEMBLE_DIR / "work/ensemble/dr4_idmap.csv"
        if not self.rel.stand_in and self.rel.key == "dr4" and not ens.exists():
            smp = pd.read_csv(ENSEMBLE_DIR / "dr4_ensemble_sample.csv", dtype=str)
            want = set(smp.source_id) | set(smp.alt_source_id.dropna())
            e = m[m.dr3_source_id.isin(want)].rename(columns={"new_source_id": "dr4_source_id"})
            e[["dr3_source_id", "dr4_source_id"]].to_csv(ens, index=False)
            info["ensemble_idmap_written"] = str(ens)
        return info

    def do_ensemble(self):
        grader = ENSEMBLE_DIR / "dr4_ensemble_grade.py"
        work = ENSEMBLE_DIR / "work/ensemble"
        info = {}
        keep = {}
        if self.rel.stand_in:  # the self-test rewrites committed files: put back the exact bytes afterwards
            keep = {p: p.read_bytes() for p in (work / "dr3_test").glob("*") if p.is_file()}
        runs = [("grade", ["--release", self.rel.name])] + ([("selftest", ["--test-dr3"])] if self.rel.stand_in else [])
        for tag, args in runs:
            r = subprocess.run([sys.executable, "-I", str(grader), *args], capture_output=True, text=True, cwd=self.root,
                               timeout=3600)
            self.path(f"ensemble/{tag}.log").write_text(r.stdout + ("\n--- stderr ---\n" + r.stderr if r.stderr else ""))
            info[tag] = {"exit": r.returncode, "tail": r.stdout.strip().splitlines()[-3:] if r.stdout.strip() else []}
        out_tag = self.rel.name.lower().replace("gaia ", "").replace(" ", "_")
        for f in (f"grade_{out_tag}.csv", f"grade_{out_tag}_summary.json"):
            src = work / f
            if src.exists():
                shutil.copy2(src, self.path(f"ensemble/{f}"))
                if self.rel.stand_in:
                    src.unlink()  # a DR3 dry-run output does not belong beside the sealed forecast
        for p, b in keep.items():
            p.write_bytes(b)
        g = self.out / f"ensemble/grade_{out_tag}.csv"
        if g.exists():
            d = pd.read_csv(g)
            info["status_counts"] = d.status.str.split(":").str[0].value_counts().to_dict()
        return info

    def do_catalogue(self):
        t = self.targets()
        ids = targets.unique_ids(t)
        idm = self.idm()
        rid = sorted({dict(zip(idm.dr3_source_id, idm.new_source_id, strict=True)).get(s, s) for s in ids}) if idm is not None else ids
        info = {}
        jobs = {"lens_catalogue": lambda: catalogue.lens_catalogue(self.arc, self.rel),
                "classifier_only": lambda: catalogue.classifier_only(self.arc, self.rel),
                "target_flags": lambda: catalogue.target_flags(self.arc, self.rel, rid),
                "target_classes": lambda: catalogue.target_classes(self.arc, self.rel, rid),
                "cones": lambda: catalogue.cones(self.arc, self.rel, t[(t.set == "nogaia") & t.t_event.apply(
                    lambda x: self.rel.in_span(x, 30))])}
        res = {}
        for name, fn in jobs.items():
            try:
                res[name] = fn()
                res[name].to_csv(self.path(f"catalogue/{name}.csv"), index=False)
                info[name] = len(res[name])
            except Exception as e:  # noqa: BLE001
                info[name] = f"error: {type(e).__name__}: {str(e)[:200]}"
                self.arc.error(f"catalogue.{name}", str(e))
        co = res.get("classifier_only")
        if co is not None and len(co):
            info["classifier_only_not_in_catalogue"] = int((~co.in_vari_microlensing).sum())
            h10 = set(pd.read_csv(self.root / "hunts/H-0010/work/gaia_ml_unpub.csv", dtype=str).source_id)
            mine = set(co[~co.in_vari_microlensing].source_id.astype(str))
            info["h0010_list_reproduced"] = {"same": len(h10 & mine), "only_h0010": len(h10 - mine), "only_release": len(mine - h10)}
        cat = res.get("lens_catalogue", pd.DataFrame())
        per, new = catalogue.crossmatch(t, cat, idm, catalogue.reference_lenses(self.root), catalogue.neowise_events(self.root))
        per.to_csv(self.path("catalogue/targets_xmatch.csv"), index=False)
        new.to_csv(self.path("catalogue/release_lenses_not_ours.csv"), index=False)
        info["targets_in_release_lens_catalogue"] = per[per.in_release_lens_catalogue].groupby("set").size().to_dict()
        if len(new):
            info["release_lenses_unreported"] = int(new.unreported.sum())
            info["release_lenses_with_neowise_event"] = int((new.neowise_event != "").sum())
        return info

    def do_epochs(self):
        t = self.targets()
        idm = self.idm()
        m = dict(zip(idm.dr3_source_id, idm.new_source_id, strict=True)) if idm is not None else {}
        cache = self.path("epoch/x").parent
        recs, status = [], []
        for tier in sorted(t.tier.unique()):
            ids = sorted({m.get(s, s) for s in t[(t.tier == tier) & (t.source_id != "")].source_id})
            log.info("tier %s: %d sources, %d per request", tier, len(ids), self.arc.chunk)
            got, r = self.arc.epoch(ids, cache=cache, on_chunk=lambda rec: log.info("chunk %s", rec))
            failed_ids = {s for x in r if not x["ok"] for s in x.get("ids", [])}
            for x in r:
                recs.append({"tier": int(tier), **{k: v for k, v in x.items() if k != "ids"}})
            for s in ids:
                st = "ok" if s in got else "error" if s in failed_ids else "absent"
                status.append(dict(release_source_id=s, tier=int(tier), status=st, n_rows=len(got[s]) if s in got else 0))
        pd.DataFrame(recs).to_csv(self.path("epoch_chunks.csv"), index=False)
        st = pd.DataFrame(status)
        flags = self.out / "catalogue/target_flags.csv"
        if flags.exists():
            fl = pd.read_csv(flags, dtype={"source_id": str})
            st = st.merge(fl.rename(columns={"source_id": "release_source_id"}), on="release_source_id", how="left")
            # "absent" is explained only if the archive says the source has no epoch photometry
            hep = st.has_epoch_photometry.astype(str).str.lower().isin(["true", "1"])
            st.loc[(st.status == "absent") & hep, "status"] = "missing (archive says it has epoch photometry)"
        st.to_csv(self.path("epoch_status.csv"), index=False)
        return {"status": st.groupby(["tier", "status"]).size().rename("n").reset_index().to_dict("records"),
                "chunks": len(recs), "chunks_failed": sum(not r["ok"] for r in recs), "requests": self.arc.n_requests}

    def do_search(self):
        xm = self.out / "catalogue/targets_xmatch.csv"
        t = pd.read_csv(xm, dtype={"source_id": str, "release_source_id": str}) if xm.exists() else self.targets()
        if "release_source_id" not in t:
            t["release_source_id"] = t.source_id
        t = t[t.tier.isin(self.tiers)]
        cache = self.out / "epoch"
        rows, cache_lc = [], {}
        for r in t[t.source_id.fillna("") != ""].itertuples():
            p = cache / f"{r.release_source_id}.csv"
            if not p.exists():
                continue
            if r.release_source_id not in cache_lc:
                cache_lc[r.release_source_id] = pd.read_csv(p, dtype={"camera": str})
            df = cache_lc[r.release_source_id]
            try:
                a = lightcurves.analyse(df, r.ra, r.dec, r.t_event if np.isfinite(r.t_event) else np.nan)
            except Exception as e:  # noqa: BLE001
                a = {"label": f"analysis error: {type(e).__name__}: {str(e)[:120]}"}
            at_event = bool(np.isfinite(r.t_event) and np.isfinite(a.get("t_peak", np.nan))
                            and abs(a["t_peak"] - r.t_event) <= max(60.0, 2 * float(a.get("lens_tE", 0) or 0)))
            rows.append(dict(source_id=r.source_id, release_source_id=r.release_source_id, set=r.set, tier=r.tier, name=r.name,
                             ra=r.ra, dec=r.dec, t_event=r.t_event, note=r.note,
                             in_release_lens_catalogue=getattr(r, "in_release_lens_catalogue", False),
                             reference_lens=getattr(r, "reference_lens", ""), gaia_peak_at_neowise_event=at_event, **a))
        m = pd.DataFrame(rows)
        cls = self.out / "catalogue/target_classes.csv"
        if len(m) and cls.exists():
            c = pd.read_csv(cls, dtype={"source_id": str}).drop_duplicates("source_id").set_index("source_id")
            m["gaia_class"] = m.release_source_id.map(c.best_class)
            m["gaia_class_score"] = m.release_source_id.map(c.best_score)
        if m.empty:
            m.to_csv(self.path("search/metrics.csv"), index=False)
            return {"n": 0}
        gc = m.get("gaia_class", pd.Series([np.nan] * len(m))).astype(str).str.upper()
        other = ~gc.isin(["NAN", "NONE", "", self.rel.microlensing_class.upper()])
        m["priority"] = [lightcurves.priority(lb, ev, ae, oc) for lb, ev, ae, oc in
                         zip(m.label, m.get("ev_status", pd.Series([None] * len(m))), m.gaia_peak_at_neowise_event, other,
                             strict=True)]
        # Known: the release's lens catalogue, a reference lens list, an Oddsky case star, an Oddsky H-0010 candidate, or a
        # catalogued kind in our hunts' classification. "known_as" says which.
        case_ids = set(t[t.set == "cases"].source_id)
        h10 = dict(zip(t[t.set == "h0010"].source_id, t[t.set == "h0010"].note, strict=False))

        def known_as(r):
            k = []
            if bool(r.in_release_lens_catalogue):
                k.append(f"{self.rel.name} vari_microlensing")
            if isinstance(r.reference_lens, str) and r.reference_lens:
                k.append(r.reference_lens)
            if r.source_id in case_ids:
                k.append("Oddsky case star")
            if r.source_id in h10 and r.set != "h0010":
                k.append(f"Oddsky H-0010 candidate ({h10[r.source_id].split(';')[0]})")
            if r.set == "h0010" and str(r.note).startswith(("known lens", "Oddsky case")):
                k.append(str(r.note).split(";")[0])
            return "; ".join(k)
        m["known_as"] = [known_as(r) for r in m.itertuples()]
        m["known"] = m.known_as != ""
        m.to_csv(self.path("search/metrics.csv"), index=False)
        rank = m[(m.priority <= 4) & ~m.known].sort_values(["priority", "A_obs_G" if "A_obs_G" in m else "priority"],
                                                           ascending=[True, False])
        # novelty, first pass: VSX (IDIA VizieR mirror; the CDS VSX page is behind a CAPTCHA) for the top of the list
        top = rank.head(60)
        if len(top):
            vx = catalogue.vsx(top[["release_source_id", "ra", "dec"]], on_error=self.arc.error)
            rank = rank.merge(vx, on="release_source_id", how="left")
        rank.to_csv(self.path("search/ranked.csv"), index=False)
        self.quicklooks(pd.concat([rank.head(30), m[m.set.isin(["sealed"])]]).drop_duplicates("release_source_id"))
        return {"n_analysed": len(m), "labels": m.groupby("set").label.value_counts().to_dict() and
                {f"{k[0]}|{k[1]}": int(v) for k, v in m.groupby("set").label.value_counts().items()},
                "ranked_unknown": len(rank),
                "ensemble_rule_at_neowise_time": m.get("ev_status", pd.Series(dtype=str)).value_counts().to_dict()}

    def quicklooks(self, sel: pd.DataFrame):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        d = self.path("search/quicklook/x").parent
        for old in d.glob("*.png"):  # priorities change between runs; stale plots would mislead
            old.unlink()
        for r in sel.itertuples():
            p = self.out / "epoch" / f"{r.release_source_id}.csv"
            if not p.exists():
                continue
            df = lightcurves.clean(pd.read_csv(p, dtype={"camera": str}))
            fig, ax = plt.subplots(figsize=(9, 3.2))
            for b, c in (("G", "k"), ("BP", "tab:blue"), ("RP", "tab:red")):
                x = df[df.band == b]
                ax.errorbar(x.t_mjd, x.mag, x.err, fmt=".", ms=3, color=c, label=b, alpha=0.8, lw=0.5)
            if np.isfinite(r.t_event):
                ax.axvline(r.t_event, color="tab:green", lw=1, ls="--", label="NEOWISE event")
            ax.invert_yaxis()
            ax.set_xlabel("MJD")
            ax.set_ylabel("mag")
            ax.set_title(f"{r.name} [{r.set}] {self.rel.name} {r.release_source_id}: {r.label}", fontsize=8)
            ax.legend(fontsize=7, ncol=4)
            fig.tight_layout()
            fig.savefig(d / f"{r.priority}_{r.set}_{r.release_source_id}.png", dpi=90)
            plt.close(fig)

    def do_report(self):
        s = self.status
        lines = [f"# H-0014 {self.rel.name} run ({'dry run: stand-in release' if self.rel.stand_in else 'release day'})", "",
                 f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}. Outputs: `{self.out}`.", "",
                 "| stage | ok | seconds | key results |", "|---|---|---|---|"]
        for st in STAGES[:-1]:
            if st in s:
                v = s[st]
                key = {k: v[k] for k in v if k not in ("ok", "seconds", "finished_utc")}
                lines.append(f"| {st} | {'yes' if v['ok'] else 'NO'} | {v['seconds']} | {json.dumps(key, default=str)[:600]} |")
        rk = self.out / "search/ranked.csv"
        if rk.exists() and rk.stat().st_size > 1:
            r = pd.read_csv(rk, dtype={"source_id": str})
            cols = [c for c in ("priority", "set", "name", "source_id", "label", "gaia_class", "vsx", "A_obs_G", "dG_fade", "t_peak",
                                "t_event", "ev_status", "colour", "ls_period", "ls_power", "lens_tE", "dbic_shape_minus_lens")
                    if c in r]
            lines += ["", "## Top of the ranked list (not known to any catalogue we hold; triage, not claims)", "",
                      md_table(r[cols].head(40))]
        if self.arc.errors:
            lines += ["", f"## Archive errors ({len(self.arc.errors)}; full list in errors.jsonl)", ""]
            lines += [f"- {e['where']}: {e['error'][:200]}" for e in self.arc.errors[:20]]
        self.path("summary.md").write_text("\n".join(lines) + "\n")
        # small results into the hunt directory (never the epoch cache)
        dest = self.root / HUNT / ("dryrun_dr3" if self.rel.stand_in else self.rel.key)
        dest.mkdir(parents=True, exist_ok=True)
        for f in ("summary.md", "status.json", "probe.json", "readiness.jsonl", "readiness.txt", "idmap.csv", "epoch_status.csv",
                  "epoch_chunks.csv", "errors.jsonl", "search/ranked.csv", "search/metrics.csv", "catalogue/cones.csv",
                  "catalogue/targets_xmatch.csv", "catalogue/release_lenses_not_ours.csv", "catalogue/classifier_only.csv",
                  "ensemble/grade.log", "ensemble/selftest.log"):
            src = self.out / f
            if src.exists():
                tgt = dest / f
                tgt.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, tgt)
        return {"summary": str(self.path("summary.md")), "copied_to": str(dest)}


def md_table(df: pd.DataFrame) -> str:
    def fmt(v):
        if isinstance(v, float):
            return "" if not np.isfinite(v) else f"{v:.3f}".rstrip("0").rstrip(".")
        return str(v).replace("|", "/")
    rows = [" | ".join(map(str, df.columns)), " | ".join("---" for _ in df.columns)]
    rows += [" | ".join(fmt(v) for v in r) for r in df.itertuples(index=False)]
    return "\n".join(f"| {x} |" for x in rows)


def run(rel: Release, stages=STAGES, tiers=(1, 2), root: Path = Path(".")) -> dict:
    r = Run(rel, tiers=tiers, root=root)
    for st in stages:
        r.stage(st)
    return r.status
