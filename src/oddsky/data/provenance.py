"""Every number in Oddsky can say where it came from."""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


class Provenance(BaseModel):
    archive: str
    query: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: str = Field(default_factory=now_iso)
    rows_raw: int = 0
    rows_kept: int = 0
    cuts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    status: str = "ok"  # ok | empty | unavailable
