from datetime import datetime, timezone

from app.access_rules import check_credential
from app.schemas import AccessDecision, CredentialStatus

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)


def test_active_credential_allowed_in_zone_and_time():
    result = check_credential("SYN-1042", "LAB-A", NOW)
    assert result.decision == AccessDecision.allow
    assert "zone_allowed" in result.reason_codes
    assert "within_time_window" in result.reason_codes


def test_expired_credential_denied():
    result = check_credential("SYN-1043", "LAB-A", NOW)
    assert result.decision == AccessDecision.deny
    assert result.credential_status == CredentialStatus.expired


def test_wrong_zone_denied():
    result = check_credential("SYN-1042", "SERVER-ROOM", NOW)
    assert result.decision == AccessDecision.deny
    assert "wrong_zone" in result.reason_codes


def test_outside_time_window_denied():
    result = check_credential("SYN-1042", "LAB-A", datetime(2026, 10, 20, 19, 0, tzinfo=timezone.utc))
    assert result.decision == AccessDecision.deny
    assert "outside_time_window" in result.reason_codes


def test_revoked_credential_denied():
    result = check_credential("SYN-1044", "ENTRY-A", NOW)
    assert result.decision == AccessDecision.deny
    assert result.credential_status == CredentialStatus.revoked


def test_unknown_credential_is_not_allowed():
    result = check_credential("SYN-9999", "LAB-A", NOW)
    assert result.decision == AccessDecision.unknown
    assert result.valid_from is None
    assert result.valid_until is None
