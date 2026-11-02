"""update_hypothesis must refuse statuses the case model cannot load."""

import pytest

from oddsky.case.model import Case, Hypothesis
from oddsky.case.store import CaseStore
from oddsky.tools import Toolbox


def test_update_hypothesis_rejects_unknown_status(tmp_path, monkeypatch):
    d = tmp_path / "OS-9999"
    d.mkdir()
    store = CaseStore(d)
    store.save(Case(id="OS-9999", title="t", target={"name": "x"},
                    hypotheses=[Hypothesis(id="H1", klass="normal", statement="s")]))
    tb = Toolbox(mode="open", author="test")
    monkeypatch.setattr(tb, "store", lambda case: store)
    with pytest.raises(ValueError):
        tb.update_hypothesis("OS-9999", "H1", "open")
    assert store.load().hypotheses[0].status == "live"
