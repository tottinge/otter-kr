from otter_kr.evidence_context import EvidenceContext


def test_context_exposes_one_git_adapter_for_composite_capabilities() -> None:
    context = EvidenceContext.from_git()

    assert context.changes is context.history
    assert context.metadata is context.history
