"""Server-side device allowance policy for Neon Shield.

This module contains the approved commercial limits. It deliberately does not
infer a customer's subscription or family membership: callers must supply
verified server-side entitlement data. Do not pass package values from a client.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DevicePackage(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    PREMIUM_FAMILY = "premium_family"


class DeviceLimitExceeded(Exception):
    """Raised when an account/member has no remaining linked-device slots."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class DeviceAllowance:
    package: DevicePackage
    member_device_count: int
    family_total_device_count: int = 0

    def __post_init__(self) -> None:
        if self.member_device_count < 0 or self.family_total_device_count < 0:
            raise ValueError("device counts must not be negative")


class DeviceLimitPolicy:
    """Fail-closed checks for the approved paid-package device allowances."""

    PREMIUM_DEVICES_PER_ACCOUNT = 3
    FAMILY_DEVICES_PER_MEMBER = 2
    FAMILY_MAX_MEMBERS = 5
    FAMILY_MAX_DEVICES = 10

    @classmethod
    def assert_can_add_device(cls, allowance: DeviceAllowance) -> None:
        """Raise when the verified package has no available device slot.

        Free-plan pairing is deliberately unchanged because its device
        allowance has not been approved in the product decision.
        """
        if allowance.package is DevicePackage.PREMIUM:
            if allowance.member_device_count >= cls.PREMIUM_DEVICES_PER_ACCOUNT:
                raise DeviceLimitExceeded("premium_device_limit_reached")
            return

        if allowance.package is DevicePackage.PREMIUM_FAMILY:
            if allowance.member_device_count >= cls.FAMILY_DEVICES_PER_MEMBER:
                raise DeviceLimitExceeded("family_member_device_limit_reached")
            if allowance.family_total_device_count >= cls.FAMILY_MAX_DEVICES:
                raise DeviceLimitExceeded("family_total_device_limit_reached")
            return

        if allowance.package is not DevicePackage.FREE:
            raise DeviceLimitExceeded("unknown_package")


def can_add_device(allowance: DeviceAllowance) -> bool:
    """Boolean adapter for callers that prefer a non-raising policy check."""
    try:
        DeviceLimitPolicy.assert_can_add_device(allowance)
    except DeviceLimitExceeded:
        return False
    return True
