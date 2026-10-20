from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccessDecision(str, Enum):
    allow = "allow"
    deny = "deny"
    review = "review"
    unknown = "unknown"


class CredentialStatus(str, Enum):
    active = "active"
    expired = "expired"
    revoked = "revoked"
    unknown = "unknown"


class CredentialReason(str, Enum):
    credential_active = "credential_active"
    credential_expired = "credential_expired"
    credential_revoked = "credential_revoked"
    zone_allowed = "zone_allowed"
    wrong_zone = "wrong_zone"
    within_time_window = "within_time_window"
    outside_time_window = "outside_time_window"
    malformed_input = "malformed_input"
    missing_policy_data = "missing_policy_data"
    conflicting_policy_data = "conflicting_policy_data"


class CredentialCheckRequest(StrictModel):
    credential_ref: str = Field(min_length=1, max_length=80, pattern=r"^SYN-[A-Za-z0-9-]+$")
    zone: str = Field(min_length=1, max_length=80)
    checked_at: datetime | None = None


class CredentialCheck(StrictModel):
    credential_ref: str
    decision: AccessDecision
    reason_codes: list[CredentialReason]
    checked_at: datetime
    zone: str
    valid_from: datetime | None
    valid_until: datetime | None
    credential_status: CredentialStatus
    policy_version: str


class ErrorCode(str, Enum):
    invalid_request = "invalid_request"
    validation_error = "validation_error"
    not_found = "not_found"
    provider_timeout = "provider_timeout"
    provider_rate_limited = "provider_rate_limited"
    provider_unavailable = "provider_unavailable"
    provider_invalid_response = "provider_invalid_response"
    dependency_unavailable = "dependency_unavailable"
    internal_error = "internal_error"


class APIError(StrictModel):
    code: ErrorCode
    message: str
    retryable: bool
    request_id: str | None
    details: dict[str, Any] | None


class NoticeStatus(str, Enum):
    success = "success"
    no_match = "no_match"
    stale = "stale"
    provider_error = "provider_error"


class SourceType(str, Enum):
    official = "official"
    public = "public"
    unknown = "unknown"


class Freshness(str, Enum):
    fresh = "fresh"
    stale = "stale"
    unknown = "unknown"


class Notice(StrictModel):
    title: str
    source_url: str
    domain: str
    excerpt: str | None
    published_at: datetime | None
    retrieved_at: datetime
    source_type: SourceType
    freshness: Freshness
    match_reason: str | None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        url = HttpUrl(value)
        if url.scheme != "https":
            raise ValueError("source_url must use HTTPS")
        return str(url)


class NoticeResult(StrictModel):
    status: NoticeStatus
    query: str
    results: list[Notice]
    retrieved_at: datetime
    freshness_threshold_seconds: int = Field(gt=0)
    error: APIError | None


class VisionStatus(str, Enum):
    observed = "observed"
    unavailable = "unavailable"
    invalid_input = "invalid_input"
    provider_error = "provider_error"


class OccupancyBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    unknown = "unknown"


class ZoneObservation(StrictModel):
    zone: str
    estimated_count: int | None = Field(default=None, ge=0)
    occupancy_band: OccupancyBand | None
    observed_at: datetime | None
    confidence_note: str | None


class VisionObservation(StrictModel):
    status: VisionStatus
    observed_at: datetime | None
    zones: list[ZoneObservation]
    limitations: list[str]
    error: APIError | None


class SourceRef(StrictModel):
    source_url: str
    domain: str
    title: str
    published_at: datetime | None
    retrieved_at: datetime
    freshness: Freshness
    match_reason: str | None


class ReviewStatus(str, Enum):
    pending = "pending"
    in_review = "in_review"
    resolved = "resolved"


class AccessIntegrityCaseCard(StrictModel):
    case_id: str
    created_at: datetime
    summary: str
    access_decision: AccessDecision
    credential_check: CredentialCheck | None
    notice_result: NoticeResult | None
    vision_observation: VisionObservation | None
    matched_rules: list[str]
    source_refs: list[SourceRef]
    uncertainty: list[str]
    review_checklist: list[str]
    review_status: ReviewStatus


class ContextSearchRequest(StrictModel):
    query: str = Field(min_length=3, max_length=500)
    location: str = Field(default="India", min_length=2, max_length=100)


class ComposeCaseRequest(StrictModel):
    credential_check: CredentialCheck | None = None
    notice_result: NoticeResult | None = None
    vision_observation: VisionObservation | None = None
