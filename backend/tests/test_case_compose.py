from datetime import datetime, timezone

from app.case_service import compose_case
from app.schemas import ComposeCaseRequest


def test_missing_credential_never_becomes_allow():
    card = compose_case(ComposeCaseRequest())
    assert card.access_decision == "unknown"
    assert card.credential_check is None
    assert any("not an all-clear" in item or "missing" in item for item in card.uncertainty)


def test_no_match_is_visible_and_has_no_sources():
    now = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)
    request = ComposeCaseRequest.model_validate({
        "notice_result": {
            "status": "no_match",
            "query": "synthetic query",
            "results": [],
            "retrieved_at": now.isoformat(),
            "freshness_threshold_seconds": 86400,
            "error": None,
        }
    })
    card = compose_case(request)
    assert card.source_refs == []
    assert any("not an all-clear" in item for item in card.uncertainty)
