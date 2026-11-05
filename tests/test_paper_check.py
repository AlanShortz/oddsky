"""Receipts for documents: a number in a text must be recomputed from the data, and every numeral declared."""
import pandas as pd
import pytest

from oddsky.paper import Claims, parse_shown


def make(tmp_path, text):
    doc = tmp_path / "note.md"
    doc.write_text(text)
    pd.DataFrame({"d": [0.44, 1.0, 1.73], "iso": [True, True, False]}).to_csv(tmp_path / "t.csv", index=False)
    return Claims(doc=doc, root=tmp_path)


def test_parse_shown_reads_precision_from_the_text():
    assert parse_shown("1.5 × 10⁻⁵") == pytest.approx((1.5e-5, 0.05e-5))
    assert parse_shown("42,759,991 sources") == (42759991.0, 0.5)
    assert parse_shown("Forty-six stars") == (46.0, 0.5)
    assert parse_shown("99.4%") == pytest.approx((99.4, 0.05))


def test_correct_numbers_pass_and_a_wrong_rate_fails(tmp_path):
    c = make(tmp_path, "Three stars change by 0.44–1.73 mag, a rate of 1.5 × 10⁻⁵.")
    t = c.table("t.csv")
    c.number("Three stars", len(t))
    c.span("0.44–1.73 mag", t.d)
    c.number("1.5 × 10⁻⁵", 631 / 42759991)
    assert c.check()["ok"]
    c = make(tmp_path, "a rate of 3 × 10⁻⁵")
    c.number("3 × 10⁻⁵", 631 / 42759991)  # the H-0016 draft's error: the denominator was one hemisphere
    assert any(f.startswith("WRONG") for f in c.check()["failures"])


def test_a_universal_statement_with_an_exception_fails(tmp_path):
    c = make(tmp_path, "All are isolated.")
    c.every("All are isolated", c.table("t.csv").iso)
    assert any(f.startswith("NOT UNIVERSAL") for f in c.check()["failures"])


def test_an_undeclared_numeral_and_a_stale_phrase_fail(tmp_path):
    c = make(tmp_path, "Of 48 stars, fourteen are real steps.")
    c.number("48 stars", 48)
    c.number("46 errors", 46)
    fails = c.check()["failures"]
    assert any(f.startswith("UNDECLARED") and "fourteen" in f for f in fails)
    assert any(f.startswith("STALE") for f in fails)


def test_identifiers_are_not_numerals_and_phrases_match_whole_numbers(tmp_path):
    c = make(tmp_path, "w1mpro from 2MASS and Gaia DR3 differ by 0.44 mag\nin W1.")
    c.number("0.44 mag in W1", 0.44)  # wraps across a line in the source
    assert c.check()["ok"]
    c = make(tmp_path, "off by 0.44 mag")
    c.number("0.4", 0.4)
    fails = c.check()["failures"]
    assert any(f.startswith("STALE") for f in fails) and any(f.startswith("UNDECLARED") for f in fails)


def test_references_are_skipped_and_ignore_needs_a_reason(tmp_path):
    c = make(tmp_path, "Observed in 2010–11.\n## References\nLang, D. 2014, AJ, 147, 108")
    c.ignore("2010–11", "survey dates")
    assert c.check()["ok"]
    with pytest.raises(ValueError):
        c.ignore("2010–11", " ")


def test_final_requires_a_review_of_exactly_this_text(tmp_path):
    c = make(tmp_path, "No numbers here.")
    c.review("review.md")
    assert c.check()["ok"] and not c.check(final=True)["ok"]
    (tmp_path / "review.md").write_text(f"document-sha256: {c.digest()}\n")
    c.failures.clear()
    assert c.check(final=True)["ok"]
    c.doc.write_text("No numbers here, edited after review.")
    assert not c.check(final=True)["ok"]
