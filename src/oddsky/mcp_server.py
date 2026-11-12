"""Oddsky as an MCP server. Your agent is the investigator; Oddsky is the observatory.

    claude mcp add oddsky -- uvx --from git+https://github.com/AlanShortz/oddsky oddsky mcp
    claude mcp add oddsky-trial -- uvx --from git+https://github.com/AlanShortz/oddsky oddsky mcp --blind trials/strange-stars-001/packets/T03

Never print to stdout here: stdout is the protocol stream. Logs go to stderr.
"""

from __future__ import annotations

import functools
import logging
import sys
from pathlib import Path

from mcp.server import MCPServer

from .tools import Toolbox, available

INSTRUCTIONS = """Oddsky gives you real telescope data on strange stars and tools to analyse it.
Work like a careful scientist: call case_overview first, then skeptic_report, look at the light
curves, and only then propose hypotheses. Record what you find with add_claim, tagging each claim
honestly (observed | computed | inferred | speculated) and citing the call_id of the tool results it
rests on. Propose explanations with add_hypothesis (classes from list_classes), say what would
falsify each, and register machine-checkable predictions with register_prediction.
The first principle is that you must not fool yourself, and you are the easiest person to fool."""


def build(mode: str = "open", blind_root: Path | None = None, author: str | None = None) -> MCPServer:
    tb = Toolbox(mode=mode, blind_root=blind_root, author=author)
    instr = INSTRUCTIONS
    if mode == "blind":
        instr += ("\n\nBLIND TRIAL: the star's identity, coordinates and calendar dates are hidden (times are "
                  "days since the first observation). Archive and literature tools are disabled. Use case "
                  f"'{blind_root.name if blind_root else '.'}'. Finish by ranking explanation classes with "
                  "add_hypothesis (confidence = your probability; they should sum to ~1).")
    mcp = MCPServer("oddsky", instructions=instr, version="0.1.0")
    for name in available(mode):
        fn = getattr(tb, name)

        @functools.wraps(fn)
        def wrapper(*a, _fn=fn, **kw):
            return _fn(*a, **kw)

        mcp.tool(name=name)(wrapper)
    return mcp


def serve(mode: str = "open", blind_root: Path | None = None, author: str | None = None) -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    build(mode, blind_root, author).run()
