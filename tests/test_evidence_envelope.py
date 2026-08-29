from otter_kr.evidence_envelope import EvidenceEnvelope


def test_evidence_envelope_has_one_typed_success_shape() -> None:
    envelope = EvidenceEnvelope("python.inventory", {"repository_root": "/repo"}, {"files": []})

    assert envelope.to_dict() == {
        "schema_version": "1",
        "status": "ok",
        "operation": "python.inventory",
        "query": {"repository_root": "/repo"},
        "data": {"files": []},
    }
