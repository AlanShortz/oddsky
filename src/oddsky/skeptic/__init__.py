"""The Skeptic: a deterministic battery of reasons a signal might not be what it seems.

It is code, not an agent, on purpose. It cannot be talked out of a warning, it gives the same
answer every time, and it never gets tired of asking "are you sure it isn't the spacecraft?"
"""

from .report import run

__all__ = ["run"]
