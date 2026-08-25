from security.auth_policy import (
    AuthorizationDecision,
    AuthorizationRequest,
    authorize,
)


TRUSTED = frozenset({"device-123"})


def request(**overrides):
    values = {
        "owner_initialized": True,
        "device_id": "device-123",
        "trusted_device_ids": TRUSTED,
        "normalized_phone": "+61400000000",
        "blocked_phone": False,
    }
    values.update(overrides)
    return AuthorizationRequest(**values)


def test_trusted_device_with_valid_identity_is_allowed():
    result = authorize(request())

    assert result.decision is AuthorizationDecision.ALLOW
    assert result.allowed is True


def test_unknown_device_is_denied():
    result = authorize(request(device_id="device-999"))

    assert result.decision is AuthorizationDecision.DENY
    assert result.reason == "unrecognised_device"


def test_blocked_identity_is_denied():
    result = authorize(request(blocked_phone=True))

    assert result.decision is AuthorizationDecision.DENY
    assert result.reason == "blocked_phone"


def test_uninitialised_owner_is_denied():
    result = authorize(request(owner_initialized=False))

    assert result.decision is AuthorizationDecision.DENY
    assert result.reason == "owner_not_initialized"


def test_missing_device_identity_is_denied():
    result = authorize(request(device_id="   "))

    assert result.decision is AuthorizationDecision.DENY
    assert result.reason == "device_identity_missing"
