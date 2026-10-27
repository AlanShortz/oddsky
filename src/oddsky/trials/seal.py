from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(trial: Path) -> str:
    h = sha256(trial / "sealed" / "answers.yaml")
    (trial / "sealed" / "answers.sha256").write_text(h + "  answers.yaml\n")
    return h


def verify(trial: Path) -> bool:
    committed = (trial / "sealed" / "answers.sha256").read_text().split()[0]
    revealed = trial / "revealed" / "answers.yaml"
    return revealed.exists() and sha256(revealed) == committed
