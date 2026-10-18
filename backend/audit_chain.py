"""Shared fail-closed validation for audit-chain backfills."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

ZERO_HASH = "0" * 64


def resolve_audit_chain_head(rows: Iterable[tuple[str, str]]) -> str:
    """Return the sole terminal hash only when every event forms one valid chain."""
    events = list(rows)
    if not events:
        return ZERO_HASH

    hashes = {event_hash for event_hash, _ in events}
    if len(hashes) != len(events):
        raise RuntimeError("audit history contains duplicate event hashes")

    children: dict[str, list[str]] = defaultdict(list)
    roots = []
    for event_hash, previous_hash in events:
        if previous_hash == ZERO_HASH:
            roots.append(event_hash)
        else:
            children[previous_hash].append(event_hash)

    if len(roots) != 1:
        raise RuntimeError("audit history must contain exactly one root")

    if any(len(next_hashes) > 1 for next_hashes in children.values()):
        raise RuntimeError("audit history contains a fork")

    visited: set[str] = set()
    current = roots[0]
    while current not in visited:
        visited.add(current)
        next_hashes = children.get(current, [])
        if not next_hashes:
            break
        current = next_hashes[0]

    if visited != hashes:
        raise RuntimeError("audit history contains an orphan or cycle")

    terminals = [event_hash for event_hash in hashes if event_hash not in children]
    if len(terminals) != 1 or terminals[0] != current:
        raise RuntimeError("audit history does not have one unambiguous terminal event")
    return current
