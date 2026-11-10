"""The schema of a finding.

Every claim carries an epistemic tag. Every hypothesis names what would hurt it. Every
prediction is machine-checkable, so the sky, not a committee, decides whether it came true.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field

Tag = Literal["observed", "computed", "inferred", "speculated"]
Ladder = Literal["observation", "anomaly", "reproduced", "interpreted", "validated", "artifact", "closed"]
HypStatus = Literal["live", "favored", "disfavored", "rejected"]

# The Strange Stars taxonomy (v0, for an astronomer to revise; see docs/OPEN_QUESTIONS.md).
CLASSES = {
    "dust_occultation": "Circumstellar dust passes in front of the star (debris, disk warp, clump).",
    "dust_formation": "The star makes its own dust (R CrB-like declines, AGB/post-AGB episodes).",
    "collision_debris": "Debris from a collision: IR excess first, optical extinction later.",
    "eclipse_companion": "A companion or its disk eclipses the star (long-period, often dusty).",
    "yso_dipper": "Young star with variable extinction from an inner disk.",
    "pulsation": "Intrinsic pulsation (Miras, semiregulars, long-period variables).",
    "eruptive": "Outbursts, flares, accretion events, novae.",
    "rotation_spots": "Starspots carried around by rotation.",
    "microlensing": "A foreground star or remnant passes almost exactly in front: achromatic, smooth, never repeats.",
    "artifact_instrumental": "The spacecraft, detector or pipeline did it.",
    "artifact_blend": "A neighbour did it: the signal is real but belongs to another star.",
    "normal": "Nothing to explain at the precision of the data.",
}
CLASS_NAMES = list(CLASSES)


def now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


class Claim(BaseModel):
    id: str
    text: str
    tag: Tag
    calls: list[str] = Field(default_factory=list, description="ledger ids of the tool calls this rests on")
    retracted: str | None = Field(default=None, description="reason, if the author withdrew the claim")
    author: str = "unknown"
    at: str = Field(default_factory=now)


class Hypothesis(BaseModel):
    id: str
    klass: str = Field(description="one of the Strange Stars classes")
    statement: str
    supports: list[str] = Field(default_factory=list, description="claim ids")
    conflicts: list[str] = Field(default_factory=list, description="claim ids")
    would_falsify: str = ""
    status: HypStatus = "live"
    confidence: float | None = None
    author: str = "unknown"
    at: str = Field(default_factory=now)


class Check(BaseModel):
    """A prediction the archive can grade by itself.

    statistic over [start, end] of series `series` (e.g. "AAVSO:V", "NEOWISE:W1"), optionally
    relative to the median over `baseline` (then positive = fainter than baseline), compared
    with `op` against `value`. Times are MJD. "brightest"/"faintest" are the extreme nightly medians;
    "amplitude" is faintest minus brightest.
    """

    series: str
    start: float
    end: float
    statistic: Literal["median", "faintest", "brightest", "amplitude"] = "median"
    baseline: tuple[float, float] | None = None
    op: Literal[">", "<"] = ">"
    value: float


class Resolution(BaseModel):
    outcome: Literal["true", "false", "unresolvable"]
    observed: float | None = None
    n_points: int = 0
    resolved_at: str = Field(default_factory=now)
    note: str = ""


class Prediction(BaseModel):
    id: str
    hypothesis: str | None = None
    statement: str
    check: Check | None = None
    probability: float = Field(ge=0, le=1, description="stated probability the check comes out true")
    resolve_by: str | None = None
    author: str = "unknown"
    registered_at: str = Field(default_factory=now)
    resolution: Resolution | None = None


class Target(BaseModel):
    name: str
    ra: float | None = None
    dec: float | None = None
    aliases: list[str] = Field(default_factory=list)
    gaia_source_id: int | None = None
    otype: str | None = None


class Reference(BaseModel):
    bibcode: str
    note: str = ""


class Case(BaseModel):
    id: str
    title: str
    hook: str = ""
    status: Ladder = "observation"
    target: Target | None = None
    summary: str = ""
    claims: list[Claim] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    literature: list[Reference] = Field(default_factory=list)
    resolution: dict[str, Any] | None = None
    hunt: str | None = None  # e.g. "H-0004": the systematic search that opened this case
    featured: bool = False
    created_at: str = Field(default_factory=now)

    def next_id(self, prefix: str, items: list) -> str:
        return f"{prefix}{len(items) + 1}"
