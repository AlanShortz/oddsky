"""Where things live: the repo (cases, trials) and the archive cache."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

# The hosted service (oddsky.hosted) gives each observer a workspace: a root of its own, and new
# cases numbered under the observer's code (ASH-0001) so they never collide with the casebook.
_root: ContextVar[Path | None] = ContextVar("oddsky_root", default=None)
_prefix: ContextVar[str] = ContextVar("oddsky_case_prefix", default="OS")


@contextmanager
def workspace(root: Path, case_prefix: str = "OS"):
    t1, t2 = _root.set(Path(root)), _prefix.set(case_prefix)
    try:
        yield
    finally:
        _root.reset(t1)
        _prefix.reset(t2)


def case_prefix() -> str:
    return _prefix.get()


def repo_root() -> Path:
    """The Oddsky repository: $ODDSKY_HOME, else the nearest ancestor holding `cases/`."""
    if (ws := _root.get()) is not None:
        return ws
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
