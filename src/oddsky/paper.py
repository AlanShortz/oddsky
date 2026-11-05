"""Receipts for documents: every number in a text that leaves the repo is recomputed from the data.

A case has a ledger and `oddsky replay`; a paper, an email or a hunt write-up had nothing, and the
first draft of the H-0016 research note carried six wrong statements that were typed from memory
(a rate with the wrong denominator, "all" where the data said 33 of 46). A claims file sits next
to the document and declares each number or universal statement with the code that recomputes it:

    def build(c):
        stars = c.table("dbf_48_unflagged_stars.csv")
        errors = stars[stars.klass != "real"]
        c.number("46 are such errors", len(errors))
        c.span("0.44–1.73 mag", errors.d1.abs())
        c.every("|R − 1| ≤ 0.07 in both bands", (errors.R1 - 1).abs() <= 0.07)
        c.external("4.9 × 10⁷ quiet stars", source="BigQuery sky2_features count, hunts/H-0016/README.md §2")
        c.ignore("2010–11", "survey dates")

`oddsky paper-check claims.py` fails if a recomputed value does not round to what the text shows,
if a universal statement has an exception, if a declared phrase is no longer in the text, or if any
numeral in the text is not covered by a declaration. `--final` also requires a referee's review of
exactly this text (a line `document-sha256: <hash>` in the review file).
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_WORDS = {w: i for i, w in enumerate(_UNITS)} | {w: 20 + 10 * i for i, w in enumerate(_TENS)}
_WORDS |= {f"{t}-{u}": 20 + 10 * i + j for i, t in enumerate(_TENS) for j, u in enumerate(_UNITS[1:10], 1)}
# "one" is left out of the scan: it is a pronoun far more often than a count
_WORD_RE = "|".join(sorted((w for w in _WORDS if w not in ("zero", "one")), key=len, reverse=True))
# a numeral is not part of an identifier (w1mpro, 2MASS, DR3) or of a longer number
_NUM_RE = re.compile(rf"(?<![A-Za-z\d.,_])\d+(?:,\d{{3}})*(?:\.\d+)?(?:\s*×\s*10[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)?(?![A-Za-z\d_])|\b(?:{_WORD_RE})\b",
                     re.IGNORECASE)


def _phrase_re(text: str) -> re.Pattern:
    """A declared phrase matches whole numbers only: '0.4' does not match inside '0.44' or '10.4'."""
    pre = r"(?<![\d.,])" if text[:1].isdigit() else ""
    post = r"(?![\d])(?!\.\d)" if text[-1:].isdigit() else ""
    return re.compile(pre + re.escape(text) + post)


def parse_shown(text: str) -> tuple[float, float]:
    """The first number in a phrase and the half-width implied by how it is printed:
    '1.5 × 10⁻⁵' -> (1.5e-5, 0.05e-5); '42,759,991' -> (42759991, 0.5); 'Forty-six' -> (46, 0.5)."""
    m = _NUM_RE.search(text)
    if not m:
        raise ValueError(f"no number in {text!r}")
    tok = m.group(0)
    if tok.lower() in _WORDS:
        return float(_WORDS[tok.lower()]), 0.5
    mant, _, exp = tok.partition("×")
    mant = mant.strip().replace(",", "").rstrip(".")
    scale = 10.0 ** int(exp.strip()[2:].translate(_SUP)) if exp else 1.0
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    return float(mant) * scale, 0.5 * 10.0 ** -decimals * scale


@dataclass
class Claims:
    doc: Path
    root: Path
    skip_after: str | None = "## References"  # citations are not results
    declared: list[tuple[str, str]] = field(default_factory=list)  # (phrase, kind)
    failures: list[str] = field(default_factory=list)
    externals: list[tuple[str, str]] = field(default_factory=list)
    tables: dict[str, str] = field(default_factory=dict)
    review_file: Path | None = None
    n_checked: int = 0

    def table(self, path: str, **kw):
        import pandas as pd

        p = (self.root / path).expanduser() if not path.startswith("~") else Path(path).expanduser()
        self.tables[path] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        return pd.read_csv(p, **kw)

    def _declare(self, text: str, kind: str) -> None:
        self.declared.append((" ".join(text.split()), kind))

    def number(self, text: str, value, scale: float = 1.0) -> None:
        """`text` is a phrase in the document; its first number must be `value` at the printed precision.
        `scale` converts the value to the printed unit (100 for a fraction printed as a percentage)."""
        self._declare(text, "number")
        shown, half = parse_shown(text)
        value = float(value) * scale
        self.n_checked += 1
        if not math.isfinite(value) or abs(value - shown) > half * (1 + 1e-9):
            self.failures.append(f"WRONG  {text!r}: the data give {value:.6g}")

    def span(self, text: str, values) -> None:
        """A printed range 'a–b' (or 'a-b', 'a to b') must be the minimum and maximum of `values`."""
        self._declare(text, "span")
        toks = [m.group(0) for m in _NUM_RE.finditer(text)][:2]
        lo, hi = float(min(values)), float(max(values))
        self.n_checked += 1
        if len(toks) < 2:
            self.failures.append(f"WRONG  {text!r}: not a range")
            return
        for tok, v, name in ((toks[0], lo, "minimum"), (toks[1], hi, "maximum")):
            shown, half = parse_shown(tok)
            if abs(v - shown) > half * (1 + 1e-9):
                self.failures.append(f"WRONG  {text!r}: the {name} in the data is {v:.6g}")

    def every(self, text: str, holds) -> None:
        """A universal statement ('all', 'none', 'each', a bound): `holds` is one boolean per row, all must be true."""
        self._declare(text, "every")
        bad = [i for i, ok in enumerate(list(holds)) if not bool(ok)]
        self.n_checked += 1
        if bad:
            self.failures.append(f"NOT UNIVERSAL  {text!r}: fails for {len(bad)} of {len(list(holds))} rows (first: row {bad[0]})")

    def external(self, text: str, source: str) -> None:
        """A number that cannot be recomputed from files in reach (a remote count). It is listed in every report."""
        self._declare(text, "external")
        self.externals.append((text, source))

    def ignore(self, text: str, why: str) -> None:
        """Numerals that are not results: dates, thresholds the author chose, section and figure numbers."""
        if not why.strip():
            raise ValueError("ignore() needs a reason")
        self._declare(text, "ignore")

    def review(self, path: str) -> None:
        self.review_file = self.root / path

    def body(self) -> str:
        text = self.doc.read_text()
        text = text.split(self.skip_after)[0] if self.skip_after and self.skip_after in text else text
        return " ".join(text.split())  # a phrase may wrap across lines in the source

    def digest(self) -> str:
        return hashlib.sha256(self.doc.read_bytes()).hexdigest()

    def check(self, final: bool = False) -> dict:
        body = self.body()
        covered = [False] * len(body)
        for text, _kind in self.declared:
            hits = [m.start() for m in _phrase_re(text).finditer(body)]
            if not hits:
                self.failures.append(f"STALE  {text!r} is declared but is not in the document")
            for h in hits:
                covered[h:h + len(text)] = [True] * len(text)
        for m in _NUM_RE.finditer(body):
            if not all(covered[m.start():m.end()]):
                ctx = body[max(0, m.start() - 45):m.end() + 30]
                self.failures.append(f"UNDECLARED  {m.group(0)!r} in '...{ctx}...'")
        reviewed = None
        if self.review_file is not None:
            reviewed = self.review_file.exists() and f"document-sha256: {self.digest()}" in self.review_file.read_text()
        if final and not reviewed:
            self.failures.append("NOT REVIEWED  no referee review of exactly this text "
                                 f"(expected 'document-sha256: {self.digest()}' in {self.review_file or 'a review file'})")
        return {"document": str(self.doc), "sha256": self.digest(), "checked": self.n_checked, "external": self.externals,
                "tables": self.tables, "reviewed": reviewed, "failures": self.failures, "ok": not self.failures}


def run(claims_file: Path, final: bool = False) -> dict:
    """Load a claims file (it defines DOCUMENT and build(c)) and check its document."""
    claims_file = Path(claims_file).resolve()
    spec = importlib.util.spec_from_file_location("oddsky_claims", claims_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    c = Claims(doc=(claims_file.parent / mod.DOCUMENT).resolve(), root=claims_file.parent)
    mod.build(c)
    return c.check(final=final)
