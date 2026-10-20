from datetime import datetime, timezone
from uuid import uuid4

from .schemas import (
    AccessDecision,
    AccessIntegrityCaseCard,
    ComposeCaseRequest,
    Freshness,
    ReviewStatus,
    SourceRef,
)


def compose_case(request: ComposeCaseRequest) -> AccessIntegrityCaseCard:
    credential = request.credential_check
    notice_result = request.notice_result
    vision = request.vision_observation
    decision = credential.decision if credential else AccessDecision.unknown
    rules = [reason.value for reason in credential.reason_codes] if credential else []
    sources: list[SourceRef] = []
    uncertainty: list[str] = []
    checklist = [
        "Confirm credential and requested zone against the authorised source of record.",
        "Verify current relevance of any public notice before relying on it.",
        "Record an authorised human decision and rationale before consequential action.",
    ]

    if credential is None:
        uncertainty.append("Credential check is missing; access decision is unknown.")
    elif decision in {AccessDecision.review, AccessDecision.unknown}:
        uncertainty.append("Credential check requires review or could not be completed.")
    if notice_result is None:
        uncertainty.append("No public-context lookup was supplied; this is not evidence that no notice exists.")
    elif notice_result.status.value == "no_match":
        uncertainty.append("TinyFish completed the search but found no usable relevant notice; this is not an all-clear.")
    elif notice_result.status.value == "stale":
        uncertainty.append("Public context is stale or its freshness cannot be established.")
    elif notice_result.status.value == "provider_error":
        uncertainty.append("Public-context provider failed; no current context is available.")
    for result in notice_result.results if notice_result else []:
        sources.append(SourceRef(
            source_url=result.source_url,
            domain=result.domain,
            title=result.title,
            published_at=result.published_at,
            retrieved_at=result.retrieved_at,
            freshness=result.freshness,
            match_reason=result.match_reason,
        ))
    if vision is not None and vision.status.value != "observed":
        uncertainty.append("Optional vision observation is unavailable or failed.")
    elif vision is not None:
        uncertainty.append("People counts are estimates from an authorised sample, not validated occupancy measurements.")

    if decision == AccessDecision.allow:
        summary = "Synthetic credential passed the deterministic access rules."
    elif decision == AccessDecision.deny:
        summary = "Synthetic credential failed one or more deterministic access rules."
    elif decision == AccessDecision.review:
        summary = "Credential check requires authorised human review."
    else:
        summary = "Access status is unknown because required credential data is unavailable."
    if notice_result is not None:
        if notice_result.status.value == "success":
            summary += " Public context was retrieved; review source provenance and relevance."
        elif notice_result.status.value == "no_match":
            summary += " No usable public notice matched the query."
        elif notice_result.status.value == "stale":
            summary += " Public context is stale or freshness is unknown."
        else:
            summary += " Public-context retrieval failed."
    return AccessIntegrityCaseCard(
        case_id=f"CASE-{uuid4().hex[:12].upper()}",
        created_at=datetime.now(timezone.utc),
        summary=summary,
        access_decision=decision,
        credential_check=credential,
        notice_result=notice_result,
        vision_observation=vision,
        matched_rules=rules,
        source_refs=sources,
        uncertainty=uncertainty,
        review_checklist=checklist,
        review_status=ReviewStatus.pending,
    )
