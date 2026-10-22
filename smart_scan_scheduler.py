"""Local timed posture-check scheduling and privacy-minimised evidence storage.

This is not an antivirus or malware-detection engine. It schedules the existing
read-only local posture checks and never labels an unavailable/uncertain result
as clear.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping, Any

INTERVAL_SECONDS = 60 * 60
APP_IDLE_SECONDS = 5 * 60
MAX_HISTORY_RECORDS = 100
SECURITY_CHECK_NAMES = {"Disk free", "Firewall", "Built-in protection"}


def local_timestamp(now: datetime | None = None) -> str:
    """Return a timezone-aware local timestamp."""
    value = now or datetime.now().astimezone()
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat(timespec="seconds")


def build_evidence_record(results: Iterable[Any], timestamp: str | None = None) -> dict[str, Any]:
    """Build an evidence record using the approved clear/non-clear policy.

    A verified-clear record contains only timestamp and status. For any
    non-clear or uncertain result, retain only the relevant non-ok check data.
    """
    items = list(results)
    stamp = timestamp or local_timestamp()
    relevant = [item for item in items if getattr(item, "name", None) in SECURITY_CHECK_NAMES]
    if relevant and all(getattr(item, "state", None) == "ok" for item in relevant):
        return {"timestamp": stamp, "status": "verified_clear"}

    issues = []
    for item in relevant:
        state = str(getattr(item, "state", "unknown"))
        if state != "ok":
            issues.append({
                "check": str(getattr(item, "name", "Unknown check")),
                "result": str(getattr(item, "result", "Unknown")),
                "state": state,
                "detail": str(getattr(item, "detail", "No diagnostic detail available.")),
            })
    if not issues:
        issues.append({
            "check": "Scheduled posture check",
            "result": "No verifiable security checks",
            "state": "uncertain",
            "detail": "No supported security checks returned a verifiable result.",
        })
    return {"timestamp": stamp, "status": "issue_or_uncertain", "issues": issues}


class SmartScanStore:
    """Small local JSON store for schedule preferences and minimal evidence."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path.home() / ".illumyx_neon_shield" / "smart_scan.json"
        self.data = self._load()

    @staticmethod
    def _default_data() -> dict[str, Any]:
        return {"enabled": True, "next_due_at": None, "history": []}

    def _load(self) -> dict[str, Any]:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return self._default_data()
            history = loaded.get("history", [])
            if not isinstance(history, list):
                history = []
            return {
                "enabled": loaded.get("enabled") is not False,
                "next_due_at": loaded.get("next_due_at") if isinstance(loaded.get("next_due_at"), str) else None,
                "history": history[-MAX_HISTORY_RECORDS:],
            }
        except (OSError, ValueError, TypeError):
            return self._default_data()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".smart-scan-", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.data, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            os.replace(temporary, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def initialise_schedule(self, now: datetime | None = None) -> None:
        if not self.data.get("next_due_at"):
            self.data["next_due_at"] = local_timestamp((now or datetime.now().astimezone()) + timedelta(seconds=INTERVAL_SECONDS))
            self.save()

    def is_due(self, now: datetime | None = None) -> bool:
        if not self.data.get("enabled", True):
            return False
        due = self.data.get("next_due_at")
        if not due:
            return False
        try:
            due_at = datetime.fromisoformat(due)
            current = now or datetime.now().astimezone()
            if current.tzinfo is None:
                current = current.astimezone()
            return current >= due_at
        except (ValueError, TypeError):
            return False

    def complete_scan(self, results: Iterable[Any], now: datetime | None = None) -> dict[str, Any]:
        stamp = local_timestamp(now)
        record = build_evidence_record(results, stamp)
        self.data.setdefault("history", []).append(record)
        self.data["history"] = self.data["history"][-MAX_HISTORY_RECORDS:]
        current = now or datetime.now().astimezone()
        self.data["next_due_at"] = local_timestamp(current + timedelta(seconds=INTERVAL_SECONDS))
        self.save()
        return record

    def defer_until_next_hour(self, now: datetime | None = None) -> None:
        current = now or datetime.now().astimezone()
        self.data["next_due_at"] = local_timestamp(current + timedelta(seconds=INTERVAL_SECONDS))
        self.save()

    def set_enabled(self, enabled: bool, now: datetime | None = None) -> None:
        self.data["enabled"] = bool(enabled)
        if enabled and not self.data.get("next_due_at"):
            current = now or datetime.now().astimezone()
            self.data["next_due_at"] = local_timestamp(current + timedelta(seconds=INTERVAL_SECONDS))
        self.save()

    def next_due_label(self) -> str:
        due = self.data.get("next_due_at")
        if not self.data.get("enabled", True):
            return "Hourly schedule paused"
        if not due:
            return "First scheduled check in about one hour"
        try:
            return "Next eligible check: " + datetime.fromisoformat(due).astimezone().strftime("%Y-%m-%d %H:%M %Z")
        except (ValueError, TypeError):
            return "Next check time unavailable"
