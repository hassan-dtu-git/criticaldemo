from datetime import datetime, timezone

from .schemas import (
    AccessDecision,
    CredentialCheck,
    CredentialReason,
    CredentialStatus,
)

POLICY_VERSION = "access-rules-v1"

# Demo-only synthetic fixtures. Real credential data must not be sent to this MVP.
SYNTHETIC_CREDENTIALS = {
    "SYN-1042": {
        "status": CredentialStatus.active,
        "zones": {"LAB-A", "ENTRY-A"},
        "valid_from": datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc),
        "valid_until": datetime(2026, 10, 20, 18, 0, tzinfo=timezone.utc),
    },
    "SYN-1043": {
        "status": CredentialStatus.expired,
        "zones": {"LAB-A"},
        "valid_from": datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc),
        "valid_until": datetime(2026, 10, 19, 18, 0, tzinfo=timezone.utc),
    },
    "SYN-1044": {
        "status": CredentialStatus.revoked,
        "zones": {"ENTRY-A"},
        "valid_from": datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc),
        "valid_until": datetime(2026, 10, 20, 18, 0, tzinfo=timezone.utc),
    },
}


def check_credential(credential_ref: str, zone: str, checked_at: datetime | None = None) -> CredentialCheck:
    now = checked_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    normalized_zone = zone.strip().upper()
    fixture = SYNTHETIC_CREDENTIALS.get(credential_ref)

    if fixture is None:
        return CredentialCheck(
            credential_ref=credential_ref,
            decision=AccessDecision.unknown,
            reason_codes=[CredentialReason.missing_policy_data],
            checked_at=now,
            zone=normalized_zone,
            valid_from=None,
            valid_until=None,
            credential_status=CredentialStatus.unknown,
            policy_version=POLICY_VERSION,
        )

    status = fixture["status"]
    valid_from = fixture["valid_from"]
    valid_until = fixture["valid_until"]
    reasons: list[CredentialReason] = []
    failures = False

    if status == CredentialStatus.revoked:
        reasons.append(CredentialReason.credential_revoked)
        failures = True
    elif status == CredentialStatus.expired:
        reasons.append(CredentialReason.credential_expired)
        failures = True
    else:
        reasons.append(CredentialReason.credential_active)

    if normalized_zone not in fixture["zones"]:
        reasons.append(CredentialReason.wrong_zone)
        failures = True
    else:
        reasons.append(CredentialReason.zone_allowed)

    if now < valid_from or now > valid_until:
        reasons.append(CredentialReason.outside_time_window)
        failures = True
    else:
        reasons.append(CredentialReason.within_time_window)

    decision = AccessDecision.deny if failures else AccessDecision.allow
    return CredentialCheck(
        credential_ref=credential_ref,
        decision=decision,
        reason_codes=reasons,
        checked_at=now,
        zone=normalized_zone,
        valid_from=valid_from,
        valid_until=valid_until,
        credential_status=status,
        policy_version=POLICY_VERSION,
    )
