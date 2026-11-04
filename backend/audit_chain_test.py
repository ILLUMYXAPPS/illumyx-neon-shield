"""Regression tests for fail-closed audit-chain head resolution."""
from __future__ import annotations

import unittest

from backend.audit_chain import ZERO_HASH, resolve_audit_chain_head


class AuditChainHeadTests(unittest.TestCase):
    def test_empty_history_uses_zero_hash(self) -> None:
        self.assertEqual(resolve_audit_chain_head([]), ZERO_HASH)

    def test_resolves_terminal_by_links_not_timestamps(self) -> None:
        # The later chain event intentionally has an earlier timestamp elsewhere in storage.
        rows = [("a" * 64, ZERO_HASH), ("b" * 64, "a" * 64)]
        self.assertEqual(resolve_audit_chain_head(rows), "b" * 64)

    def test_rejects_multiple_roots(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exactly one root"):
            resolve_audit_chain_head([("a" * 64, ZERO_HASH), ("b" * 64, ZERO_HASH)])

    def test_rejects_forks(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "fork"):
            resolve_audit_chain_head([
                ("a" * 64, ZERO_HASH),
                ("b" * 64, "a" * 64),
                ("c" * 64, "a" * 64),
            ])

    def test_rejects_orphans_and_cycles(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "orphan or cycle"):
            resolve_audit_chain_head([
                ("a" * 64, ZERO_HASH),
                ("b" * 64, "c" * 64),
                ("c" * 64, "b" * 64),
            ])


if __name__ == "__main__":
    unittest.main()
