from otter_kr.change_evidence import TermChangeEvidence


def test_term_change_evidence_keeps_current_and_history_distinct() -> None:
    report = TermChangeEvidence("Widget", {"nodes": []}, {"files": []})

    assert report.to_dict() == {
        "term": "Widget",
        "current": {"nodes": []},
        "history": {"files": []},
    }
