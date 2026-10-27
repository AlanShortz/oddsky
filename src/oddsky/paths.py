"""Where things live: the repo (cases, trials) and the archive cache."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """The Oddsky repository: $ODDSKY_HOME, else the nearest ancestor holding `cases/`."""
    if env := os.environ.get("ODDSKY_HOME"):
        return Path(env).expanduser().resolve()
    here = Path.cwd().resolve()
    for p in (here, *here.parents):
        if (p / "cases").is_dir() and (p / "pyproject.toml").exists():
            return p
    # Installed from PyPI and run outside a checkout: work in the current directory.
    return here


def cases_dir() -> Path:
    return repo_root() / "cases"


def trials_dir() -> Path:
    return repo_root() / "trials"


def cache_dir() -> Path:
    p = Path(os.environ.get("ODDSKY_CACHE", "~/.cache/oddsky")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p
