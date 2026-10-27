"""Reading and writing case directories.

cases/OS-0001/
  case.yaml            claims, hypotheses, predictions (the argument)
  data/*.parquet       light curves, one file per survey (the evidence)
  data/provenance.yaml where every row came from and which cuts removed what
  data/context.json    Gaia context, neighbours, survey metadata
  ledger.jsonl         every tool call, its arguments and a digest of its result (replayable)
  investigations/*.md  write-ups, one per investigator
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from ..paths import cases_dir
from .model import Case, now

ID_RE = re.compile(r"^(OS|T|H)-?\d+", re.I)


class CaseStore:
    """A case directory. Works the same for open cases and blind trial packets."""

    def __init__(self, path: Path):
        self.path = Path(path)

    # -- location -----------------------------------------------------------------------------
    @classmethod
    def find(cls, ref: str) -> CaseStore:
        p = Path(ref).expanduser()
        if (p / "case.yaml").exists():
            return cls(p)
        root = cases_dir()
        for d in sorted(root.glob("*")) if root.exists() else []:
            if d.name.lower() == ref.lower() or d.name.lower().startswith(ref.lower() + "-"):
                return cls(d)
        for d in sorted(root.glob("*")) if root.exists() else []:
            if (d / "case.yaml").exists():
                c = yaml.safe_load((d / "case.yaml").read_text())
                names = [c.get("target", {}).get("name", "")] + c.get("target", {}).get("aliases", [])
                if any(ref.lower() == str(n).lower() for n in names):
                    return cls(d)
        raise FileNotFoundError(f"no case '{ref}' (looked in {root})")

    @staticmethod
    def next_case_id() -> str:
        root = cases_dir()
        nums = [int(m.group(0)[3:]) for d in root.glob("OS-*") if (m := re.match(r"OS-\d+", d.name))]
        return f"OS-{(max(nums) + 1 if nums else 1):04d}"

    # -- the argument ---------------------------------------------------------------------------
    def load(self) -> Case:
        return Case.model_validate(yaml.safe_load((self.path / "case.yaml").read_text()))

    def save(self, case: Case) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        data = case.model_dump(mode="json", exclude_none=True)
        (self.path / "case.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100))

    # -- the evidence ---------------------------------------------------------------------------
    @property
    def data(self) -> Path:
        return self.path / "data"

    def surveys(self) -> list[str]:
        return sorted(p.stem for p in self.data.glob("*.parquet")) if self.data.exists() else []

    def series(self, survey: str) -> pd.DataFrame:
        f = self.data / f"{survey.lower()}.parquet"
        if not f.exists():
            raise FileNotFoundError(f"{self.path.name} has no {survey} data (have: {', '.join(self.surveys()) or 'none'})")
        return pd.read_parquet(f)

    def write_series(self, survey: str, df: pd.DataFrame) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.data / f"{survey.lower()}.parquet", index=False)

    def context(self) -> dict:
        f = self.data / "context.json"
        return json.loads(f.read_text()) if f.exists() else {}

    def write_context(self, ctx: dict) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "context.json").write_text(json.dumps(ctx, indent=2, default=_jsonable))

    def provenance(self) -> dict:
        f = self.data / "provenance.yaml"
        return (yaml.safe_load(f.read_text()) or {}) if f.exists() else {}

    def write_provenance(self, prov: dict) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "provenance.yaml").write_text(yaml.safe_dump(prov, sort_keys=False, width=100))

    # -- the ledger -----------------------------------------------------------------------------
    def log_call(self, tool: str, args: dict[str, Any], result: Any, author: str) -> str:
        from .. import __version__

        entries = self.ledger()
        cid = f"K{len(entries) + 1}"
        rec = {"id": cid, "tool": tool, "args": args, "digest": digest(result), "digest10": digest10(result),
               "author": author, "at": now(), "oddsky": __version__, "platform": platform_tag()}
        with (self.path / "ledger.jsonl").open("a") as f:
            f.write(json.dumps(rec, default=_jsonable) + "\n")
        return cid

    def ledger(self) -> list[dict]:
        f = self.path / "ledger.jsonl"
        if not f.exists():
            return []
        return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def digest(result: Any) -> str:
    """Exact digest (full float precision): reproducible on the same platform and library versions."""
    return hashlib.sha256(json.dumps(result, sort_keys=True, default=_jsonable).encode()).hexdigest()[:16]


def _round(o, sig: int = 10):
    if isinstance(o, float):
        return float(f"{o:.{sig}g}") if math.isfinite(o) else str(o)
    if isinstance(o, dict):
        return {k: _round(v, sig) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v, sig) for v in o]
    return o


def digest10(result: Any) -> str:
    """Digest of the result with floats rounded to 10 significant figures: stable across CPU
    architectures, where SIMD summation order and fused multiply-adds change the last bits."""
    canon = _round(json.loads(json.dumps(result, default=_jsonable)))
    return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()[:16]


def platform_tag() -> str:
    import platform
    import sys

    return f"{sys.platform}-{platform.machine()}"


def _jsonable(o):
    import numpy as np

    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)
