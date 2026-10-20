# SecureEntry Lens — Minimal PRD & API Contract

**Status:** Draft for team approval. Contract/documentation only; no application code is authorized.
**Product:** SecureEntry Lens — Security Verification & Incident Intelligence
**Signature feature:** Access Integrity Case Card
**Source of truth:** KRITICAL HACKS ’26 Final Master Plan supplied by the team.

## 1. Product requirements

### Problem and users
Facilities and controlled venues often keep credentials, zone/time permissions, observations, and public notices in separate tools. Security supervisors and facility operations teams need a traceable way to cross-check these signals. Event operations are a secondary audience.

### P0 — required MVP
1. **Deterministic credential/access check** using synthetic credentials only. Check credential status, allowed zone, and time window. Return explicit allow, deny, review, or unknown decisions and reason codes.
2. **Real TinyFish Search → Fetch** for relevant official/public notices. Preserve title, URL/domain, excerpt, publication time when supplied, retrieval time, source type, and freshness/status. Keep provider credentials server-side.
3. **Access Integrity Case Card** composed from actual API results. Show the access decision and reason, notice evidence/provenance, timestamps/freshness, uncertainty, and human-review checklist. A notice is contextual information, not evidence that a person is involved.
4. **Failure-aware API/UI** for invalid input, no result, stale data, timeout/provider failure, and unavailable optional dependencies. Missing or failed information must never become an all-clear.
5. **Reproducible setup and tests** documented from the actual repository. Never claim an unrun command or feature is verified.

### P1 — only after P0 works
- Minimal review/audit timeline: case ID, event time, reviewer status/action/reason; store minimal data.
- Optional OpenCV/pretrained people-count estimate from an authorised sample image or short clip, with configured zones, estimated count/occupancy band, observation time, and limitations.
- Synthetic guest QR/replay checks only if time remains and they do not endanger the core path.

### Non-goals
- Face recognition, persistent identity tracking, person-level criminality/dangerousness scoring, criminal-record aggregation, automatic police referral, or automated enforcement.
- Claims of validated life-safety/security certification.
- Claims of tailgating, weapon, threat, or blocked-exit detection unless separately implemented and tested; these are not MVP promises.
- Live/multi-camera streams, broad analytics, notifications, custom model training, or multi-agent orchestration.
- Forcing a public notice match, treating a notice as proof of causation, or fabricating sources/results.
- Treating TinyFish-fetched text as trusted instructions. It is untrusted external data.

## 2. Primary user journey

1. An authorised operator enters a synthetic credential reference, target zone, and check time.
2. The API validates the request and deterministically checks credential status, zone permission, and time window.
3. The operator enters a location/event query for public context. The backend calls TinyFish Search, conservatively selects a relevant official/public result, then fetches it.
4. The backend composes an Access Integrity Case Card with the credential decision, rule reasons, notice result and provenance, freshness, uncertainty, and review checklist.
5. The operator reviews the evidence. Any missing, stale, conflicting, or provider-failed input is visibly marked unknown/review; no consequential action is automated.

## 3. Contract-wide conventions

- JSON field names are snake_case. Objects must not silently rename fields.
- Timestamps are RFC 3339 date-times with timezone; emit UTC (Z) when possible. A timestamp not supplied by a source is null, not guessed.
- **Required vs nullable:** every field listed in a schema is required unless marked optional. Nullable means the key must still be present and its value may be null. Do not omit nullable keys.
- Empty collections use [] rather than null. Unknown scalar values use null only where the schema allows it; use a status/reason to explain why.
- Enums are case-sensitive lowercase strings. Unknown enum values must not be invented; API clients should handle unrecognised future values safely.
- source_url must be a URL returned by the provider. domain is derived from that URL. Do not fabricate provenance.
- Provider response text is untrusted data and must never override application policy.
- These schemas define API payloads, not database models. Do not add person-identifying data to synthetic credential flows.
- API errors use one stable envelope. Do not return stack traces, secrets, or provider credentials.

## 4. P0 routes

| Method and route | Purpose | Contract output |
|---|---|---|
| GET /api/health | Service status | status, version, dependency status if available |
| POST /api/credential/check | Deterministic credential/access-policy check | CredentialCheck |
| POST /api/context/search-fetch | TinyFish public-notice search then fetch | NoticeResult |
| POST /api/cases/compose | Compose review card from supplied real results | AccessIntegrityCaseCard |
| POST /api/vision/observe | P1 optional authorised sample observation only | VisionObservation; if not implemented, report unavailable rather than simulate output |
| POST /api/cases/{case_id}/review | P1 reviewer action/audit event | Deferred until approved for P1 |

## 5. Stable schemas

### 5.1 CredentialCheck

**Purpose:** deterministic result of checking a synthetic credential against status, zone, and time rules.

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| credential_ref | string | No | Synthetic identifier only; no real name or identity document |
| decision | enum | No | allow, deny, review, unknown |
| reason_codes | array of enum | No | Prefer explicit reasons; empty only when no rule reason applies |
| checked_at | datetime | No | Time the check was evaluated |
| zone | string | No | Requested zone identifier |
| valid_from | datetime | Yes | Null if unavailable/not applicable |
| valid_until | datetime | Yes | Null if unavailable/not applicable |
| credential_status | enum | No | active, expired, revoked, unknown |
| policy_version | string | No | Version/name of deterministic rule set |

Allowed reason_codes: credential_active, credential_expired, credential_revoked, zone_allowed, wrong_zone, within_time_window, outside_time_window, malformed_input, missing_policy_data, conflicting_policy_data.

Decision semantics:
- allow: all required checks passed with sufficient data.
- deny: a deterministic policy rule explicitly failed (for example expired or wrong zone).
- review: authorised human review is required (for example conflicting policy inputs).
- unknown: the check cannot be completed because required data is missing/unavailable/invalid. Never map unknown to allow.

Example — valid synthetic credential:

    {
      "credential_ref": "SYN-1042",
      "decision": "allow",
      "reason_codes": ["credential_active", "zone_allowed", "within_time_window"],
      "checked_at": "2026-10-20T09:00:00Z",
      "zone": "LAB-A",
      "valid_from": "2026-10-20T08:00:00Z",
      "valid_until": "2026-10-20T18:00:00Z",
      "credential_status": "active",
      "policy_version": "access-rules-v1"
    }

Example — expired credential:

    {
      "credential_ref": "SYN-1043",
      "decision": "deny",
      "reason_codes": ["credential_expired"],
      "checked_at": "2026-10-20T09:00:00Z",
      "zone": "LAB-A",
      "valid_from": "2026-10-19T08:00:00Z",
      "valid_until": "2026-10-19T18:00:00Z",
      "credential_status": "expired",
      "policy_version": "access-rules-v1"
    }

### 5.2 VisionObservation (P1)

**Purpose:** optional estimated people-count/occupancy observation from an authorised sample. This is not identity recognition or a validated safety measurement.

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| status | enum | No | observed, unavailable, invalid_input, provider_error |
| observed_at | datetime | Yes | Null when no observation was produced |
| zones | array of ZoneObservation | No | Empty when no zone result exists |
| limitations | array of string | No | Include material estimator/sample limitations |
| error | APIError or null | Yes | Non-null for unavailable, invalid_input, or provider_error; null for observed |

ZoneObservation fields:
- zone: string, required, non-null.
- estimated_count: integer or null; non-negative when present.
- occupancy_band: enum or null: low, medium, high, unknown.
- observed_at: datetime or null.
- confidence_note: string or null; qualitative explanation only, not an uncalibrated numeric confidence score.

No sample/image bytes or personal media should be stored in the contract response. If vision is not implemented, return unavailable; do not use fabricated counts.

Example — authorised sample processed:

    {
      "status": "observed",
      "observed_at": "2026-10-20T09:02:00Z",
      "zones": [
        {
          "zone": "ENTRY-A",
          "estimated_count": 7,
          "occupancy_band": "low",
          "observed_at": "2026-10-20T09:02:00Z",
          "confidence_note": "Estimate from one authorised sample; not a validated occupancy measurement."
        }
      ],
      "limitations": ["Single sample only", "Counts are estimates", "No identity recognition"],
      "error": null
    }

### 5.3 NoticeResult

**Purpose:** outcome and provenance of the TinyFish Search → Fetch public-context workflow.

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| status | enum | No | success, no_match, stale, provider_error |
| query | string | No | Query sent by backend |
| results | array of Notice | No | Empty for no_match; never null |
| retrieved_at | datetime | No | Time workflow completed, including no-match/error |
| freshness_threshold_seconds | integer | No | Applied freshness threshold; positive integer |
| error | APIError or null | Yes | Non-null only for provider_error; null otherwise |

Notice fields:
- title: string, required, non-null.
- source_url: string, required, non-null, valid HTTP(S) URL returned by provider.
- domain: string, required, non-null, host/domain derived from source_url.
- excerpt: string or null; null if no usable excerpt was returned.
- published_at: datetime or null; null if source did not publish a timestamp.
- retrieved_at: datetime, required, non-null.
- source_type: enum, required, non-null: official, public, unknown.
- freshness: enum, required, non-null: fresh, stale, unknown.
- match_reason: string or null; concise relevance explanation, never a claim of causation.

Status rules:
- success: at least one fetched notice is usable; results is non-empty.
- no_match: search completed without a relevant usable notice; results is empty and error is null.
- stale: one or more candidate notices exist but are outside the configured freshness threshold or freshness cannot be established; preserve evidence and mark freshness explicitly. Do not present stale context as current.
- provider_error: Search or Fetch failed, timed out, was rate-limited, or returned unusable provider data; error is non-null. Do not fabricate results.

Example — success:

    {
      "status": "success",
      "query": "official transit service notice near Venue A",
      "results": [
        {
          "title": "Service advisory",
          "source_url": "https://example.gov/notices/service-advisory",
          "domain": "example.gov",
          "excerpt": "Service changes are in effect near Venue A.",
          "published_at": "2026-10-20T07:30:00Z",
          "retrieved_at": "2026-10-20T09:03:00Z",
          "source_type": "official",
          "freshness": "fresh",
          "match_reason": "Notice mentions the requested venue area."
        }
      ],
      "retrieved_at": "2026-10-20T09:03:00Z",
      "freshness_threshold_seconds": 86400,
      "error": null
    }

Example — no match:

    {
      "status": "no_match",
      "query": "official notice for synthetic query Q-17",
      "results": [],
      "retrieved_at": "2026-10-20T09:03:00Z",
      "freshness_threshold_seconds": 86400,
      "error": null
    }

Example — stale result:

    {
      "status": "stale",
      "query": "official transit service notice near Venue A",
      "results": [
        {
          "title": "Older service advisory",
          "source_url": "https://example.gov/notices/older-advisory",
          "domain": "example.gov",
          "excerpt": "An earlier service change was announced.",
          "published_at": "2026-10-15T07:30:00Z",
          "retrieved_at": "2026-10-20T09:03:00Z",
          "source_type": "official",
          "freshness": "stale",
          "match_reason": "Area matches, but the notice is outside the freshness threshold."
        }
      ],
      "retrieved_at": "2026-10-20T09:03:00Z",
      "freshness_threshold_seconds": 86400,
      "error": null
    }

Example — provider error:

    {
      "status": "provider_error",
      "query": "official transit service notice near Venue A",
      "results": [],
      "retrieved_at": "2026-10-20T09:03:00Z",
      "freshness_threshold_seconds": 86400,
      "error": {
        "code": "provider_unavailable",
        "message": "Public context provider is temporarily unavailable.",
        "retryable": true,
        "request_id": "req-7f2a",
        "details": null
      }
    }

### 5.4 AccessIntegrityCaseCard

**Purpose:** explainable review object composed from the credential result and any available notice/vision context. It is not a prediction, accusation, or enforcement decision.

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| case_id | string | No | Stable opaque case identifier |
| created_at | datetime | No | Card creation time |
| summary | string | No | Neutral, evidence-based summary |
| access_decision | enum | No | allow, deny, review, unknown; copied from credential check, not inferred from notice |
| credential_check | CredentialCheck or null | Yes | Null only if check could not be obtained; decision must then be unknown |
| notice_result | NoticeResult or null | Yes | Null if context lookup was not requested/attempted |
| vision_observation | VisionObservation or null | Yes | Null when P1 vision is not requested/implemented |
| matched_rules | array of string | No | Deterministic rule IDs/reasons; empty if unavailable |
| source_refs | array of SourceRef | No | Evidence provenance; empty if no source was returned |
| uncertainty | array of string | No | Explicit unknowns, stale/conflicting inputs, and limitations |
| review_checklist | array of string | No | Concrete checks for an authorised human reviewer |
| review_status | enum | No | pending, in_review, resolved |

SourceRef fields:
- source_url: string, required, non-null.
- domain: string, required, non-null.
- title: string, required, non-null.
- published_at: datetime or null.
- retrieved_at: datetime, required, non-null.
- freshness: enum, required, non-null: fresh, stale, unknown.
- match_reason: string or null.

Rules:
- A notice match means potential contextual relevance only, not that a person caused or is involved in an incident.
- If credential check is missing, malformed, or incomplete, access_decision must be unknown or review, never allow.
- Stale/failed/missing public context must appear in uncertainty and/or the card summary.
- A public notice cannot upgrade a credential decision to allow or deny.
- Human review is required before any consequential action. The MVP does not automate enforcement.

Example — composed card with a stale notice:

    {
      "case_id": "CASE-2026-0001",
      "created_at": "2026-10-20T09:04:00Z",
      "summary": "Synthetic credential passed deterministic access rules. Related public context is stale and requires verification.",
      "access_decision": "allow",
      "credential_check": {
        "credential_ref": "SYN-1042",
        "decision": "allow",
        "reason_codes": ["credential_active", "zone_allowed", "within_time_window"],
        "checked_at": "2026-10-20T09:00:00Z",
        "zone": "LAB-A",
        "valid_from": "2026-10-20T08:00:00Z",
        "valid_until": "2026-10-20T18:00:00Z",
        "credential_status": "active",
        "policy_version": "access-rules-v1"
      },
      "notice_result": {
        "status": "stale",
        "query": "official transit service notice near Venue A",
        "results": [
          {
            "title": "Older service advisory",
            "source_url": "https://example.gov/notices/older-advisory",
            "domain": "example.gov",
            "excerpt": "An earlier service change was announced.",
            "published_at": "2026-10-15T07:30:00Z",
            "retrieved_at": "2026-10-20T09:03:00Z",
            "source_type": "official",
            "freshness": "stale",
            "match_reason": "Area matches, but the notice is outside the freshness threshold."
          }
        ],
        "retrieved_at": "2026-10-20T09:03:00Z",
        "freshness_threshold_seconds": 86400,
        "error": null
      },
      "vision_observation": null,
      "matched_rules": ["credential_active", "zone_allowed", "within_time_window"],
      "source_refs": [
        {
          "source_url": "https://example.gov/notices/older-advisory",
          "domain": "example.gov",
          "title": "Older service advisory",
          "published_at": "2026-10-15T07:30:00Z",
          "retrieved_at": "2026-10-20T09:03:00Z",
          "freshness": "stale",
          "match_reason": "Area matches, but the notice is outside the freshness threshold."
        }
      ],
      "uncertainty": [
        "Public notice is stale; current relevance is unverified.",
        "Notice is contextual information and does not identify or implicate any person."
      ],
      "review_checklist": [
        "Confirm credential and zone details against the authorised source of record.",
        "Verify whether the public notice is still current.",
        "Record a human decision and rationale before consequential action."
      ],
      "review_status": "pending"
    }

### 5.5 APIError

**Purpose:** stable error envelope for invalid requests and failed dependencies.

| Field | Type | Nullable | Rule |
|---|---|---:|---|
| code | enum | No | Stable machine-readable code |
| message | string | No | Safe user-facing message; no secrets/stack traces |
| retryable | boolean | No | Whether retry may reasonably succeed |
| request_id | string | Yes | Correlation ID if available |
| details | object or null | Yes | Safe field-level validation details; never raw provider payloads or credentials |

Allowed codes: invalid_request, validation_error, not_found, provider_timeout, provider_rate_limited, provider_unavailable, provider_invalid_response, dependency_unavailable, internal_error.

Example — invalid input:

    {
      "code": "validation_error",
      "message": "The requested zone is required.",
      "retryable": false,
      "request_id": "req-11a0",
      "details": {"field": "zone", "issue": "required"}
    }

Example — provider error:

    {
      "code": "provider_timeout",
      "message": "Public context provider did not respond in time.",
      "retryable": true,
      "request_id": "req-11a1",
      "details": null
    }

## 6. Acceptance criteria

### P0 credential/access
- Valid synthetic credential in permitted zone/time returns allow and explicit reason codes.
- Expired/revoked credential, wrong zone, and outside-window cases return deterministic deny with relevant reason codes.
- Malformed or incomplete policy data returns review or unknown, never allow.
- Unit tests cover valid, expired, wrong-zone, wrong-time, revoked, malformed, and missing/conflicting policy data.

### P0 TinyFish Search → Fetch
- Backend performs a real Search then Fetch request when credentials are configured.
- Result preserves source URL/domain, title, excerpt if present, publication time if present, retrieval time, source type, and freshness.
- No-match, stale, timeout, rate-limit, malformed response, and provider-unavailable outcomes are distinguishable and schema-valid.
- API key remains server-side and is not printed in logs or committed.
- No fake result is presented as live provider output.

### P0 Case Card and failure handling
- Card is built from actual contract-shaped outputs and displays access decision/reasons, provenance, timestamps/freshness, uncertainty, and reviewer checklist.
- Every notice source reference maps to a returned URL; no source or match is invented.
- No-match is shown as no match, not as proof of safety.
- Stale/missing/provider-error inputs are visible and do not become an all-clear.
- A notice match is described only as potential relevance; no person-level inference or automated enforcement occurs.

### P0 reproducibility
- README documents only commands confirmed against repository files and tests actually run.
- Synthetic data is used for credential examples; secrets and private media are excluded.
- Tests and end-to-end demo results are reported honestly, including unrun checks.

### P1 optional
- Vision is omitted or clearly marked unavailable unless an authorised sample can be processed repeatably.
- Any count is labelled an estimate with sample/model limitations; no identity recognition.
- Review/audit persistence is minimal and added only after P0 approval.

## 7. Proposed file ownership (approval required)

This is a proposal, not an assertion about existing files. Confirm the actual repository structure before assigning implementation paths.

| Owner | Exclusive ownership proposal | Responsibilities |
|---|---|---|
| A — Access/backend | backend/app/api/credential.py, backend/app/services/access_rules.py, backend/app/schemas/credential.py, backend/tests/test_access_rules.py | Deterministic checks, input validation, credential tests |
| B — TinyFish context | backend/app/api/context.py, backend/app/services/tinyfish.py, backend/app/schemas/notice.py, related provider tests | Real Search → Fetch, provenance, freshness, timeout/rate-limit/error handling |
| C — Frontend/Case Card | frontend/src/ | Dashboard, request wiring, result and failure states, Case Card UI |
| D — Integrator/QA | docs/contracts.md, root configuration, README.md, integration tests; owns merges | Contract authority, shared configuration, end-to-end verification, setup/release documentation |

**Shared contract rule:** no owner independently renames a route, field, enum, or nullable rule. Proposed routes and file paths must be reconciled with the actual repository before implementation. The integrator approves contract changes and merges. Optional vision has no implementation owner until P0 is working.

## 8. Approval checklist — no implementation before sign-off

- [ ] Approve enum values and null/empty rules in this document.
- [ ] Approve route names and NoticeResult status semantics.
- [ ] Approve proposed owner/file split after checking the actual repository tree.
- [ ] Confirm whether P1 vision and review/audit timeline remain deferred.
- [ ] Only after approval, implement against this contract and test success, no-match, stale, invalid-input, and provider-error cases.
