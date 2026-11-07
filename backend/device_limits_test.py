"""Tests for the approved server-side device allowance policy."""
import unittest

from backend.device_limits import (
    DeviceAllowance,
    DeviceLimitExceeded,
    DeviceLimitPolicy,
    DevicePackage,
    can_add_device,
)


class DeviceLimitPolicyTests(unittest.TestCase):
    def test_premium_allows_first_three_devices(self):
        for count in range(3):
            with self.subTest(existing=count):
                self.assertTrue(can_add_device(DeviceAllowance(DevicePackage.PREMIUM, count)))

    def test_premium_rejects_fourth_device(self):
        allowance = DeviceAllowance(DevicePackage.PREMIUM, 3)
        with self.assertRaises(DeviceLimitExceeded) as caught:
            DeviceLimitPolicy.assert_can_add_device(allowance)
        self.assertEqual(caught.exception.reason, "premium_device_limit_reached")

    def test_family_member_can_have_two_devices(self):
        for count in range(2):
            with self.subTest(existing=count):
                self.assertTrue(can_add_device(DeviceAllowance(
                    DevicePackage.PREMIUM_FAMILY, count, family_total_device_count=8
                )))

    def test_family_rejects_third_device_for_one_member(self):
        allowance = DeviceAllowance(
            DevicePackage.PREMIUM_FAMILY, 2, family_total_device_count=8
        )
        with self.assertRaises(DeviceLimitExceeded) as caught:
            DeviceLimitPolicy.assert_can_add_device(allowance)
        self.assertEqual(caught.exception.reason, "family_member_device_limit_reached")

    def test_family_rejects_eleventh_household_device(self):
        allowance = DeviceAllowance(
            DevicePackage.PREMIUM_FAMILY, 1, family_total_device_count=10
        )
        with self.assertRaises(DeviceLimitExceeded) as caught:
            DeviceLimitPolicy.assert_can_add_device(allowance)
        self.assertEqual(caught.exception.reason, "family_total_device_limit_reached")

    def test_family_allows_tenth_device_when_member_has_capacity(self):
        self.assertTrue(can_add_device(DeviceAllowance(
            DevicePackage.PREMIUM_FAMILY, 1, family_total_device_count=9
        )))

    def test_member_limit_is_checked_even_if_family_has_unused_capacity(self):
        self.assertFalse(can_add_device(DeviceAllowance(
            DevicePackage.PREMIUM_FAMILY, 2, family_total_device_count=4
        )))

    def test_negative_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            DeviceAllowance(DevicePackage.PREMIUM, -1)

    def test_free_allowance_is_not_changed_by_this_decision(self):
        self.assertTrue(can_add_device(DeviceAllowance(DevicePackage.FREE, 100)))


if __name__ == "__main__":
    unittest.main()
