"""Platform telemetry adapters for Neon Forensics.

These collectors are deliberately observation-only and local. They feed the
existing deny-by-default Neon Forensics policy and never perform remote scans,
hack-back actions, credential extraction, or collection of private content.
"""
from __future__ import annotations

import hashlib
import json
import platform
import plistlib
import re
import socket
import subprocess
from pathlib import Path
from typing import Any

from neon_forensics import CollectionClass, Incident, IncidentSeverity, add_event


def _run(command: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, PermissionError):
        return None


def collect_windows_posture(incident: Incident) -> None:
    """Collect a small Windows posture snapshot using local OS interfaces."""
    if platform.system().lower() != "windows":
        return
    os_version = platform.version()
    add_event(
        incident,
        event_type="windows_posture",
        platform="windows",
        source="local_os",
        severity=IncidentSeverity.INFO,
        confidence=1.0,
        data={
            "platform": "windows",
            "os_version": platform.release(),
            "os_build": os_version,
            "architecture": platform.machine(),
            "device_model": platform.node(),
        },
    )


def collect_windows_security_events(incident: Incident, *, max_events: int = 25) -> int:
    """Read selected local Windows Security events when available.

    We use wevtutil rather than installing or enabling auditing. Existing logs
    are observed only. Event 4625 (failed logon) and 4688 (process creation)
    are useful forensic anchors; command-line data is intentionally not parsed
    or stored because it may contain secrets.
    """
    if platform.system().lower() != "windows":
        return 0

    query = "*[System[(EventID=4625 or EventID=4688)]]"
    raw = _run(["wevtutil", "qe", "Security", "/q:" + query, "/f:RenderedXml", "/c:" + str(max_events)], timeout=12)
    if not raw:
        return 0

    count = 0
    chunks = re.findall(r"<Event[\\s\\S]*?</Event>", raw)
    for xml in chunks:
        event_id = re.search(r"<EventID[^>]*>(\\d+)</EventID>", xml)
        created = re.search(r"SystemTime=\"([^\"]+)\"", xml)
        if not event_id:
            continue
        eid = event_id.group(1)
        event_type = "windows_failed_logon" if eid == "4625" else "windows_process_creation"
        severity = IncidentSeverity.MEDIUM if eid == "4625" else IncidentSeverity.INFO
        add_event(
            incident,
            event_type=event_type,
            platform="windows",
            source="windows_security_event_log",
            severity=severity,
            confidence=1.0,
            data={
                "event_type": event_type,
                "event_timestamp_utc": created.group(1) if created else "",
                "event_id": eid,
            },
        )
        count += 1
    return count


def collect_macos_posture(incident: Incident) -> None:
    """Collect a minimal macOS posture snapshot using public local commands."""
    if platform.system().lower() != "darwin":
        return
    add_event(
        incident,
        event_type="macos_posture",
        platform="macos",
        source="local_os",
        severity=IncidentSeverity.INFO,
        confidence=1.0,
        data={
            "platform": "macos",
            "os_version": platform.mac_ver()[0],
            "architecture": platform.machine(),
            "device_model": _run(["sysctl", "-n", "hw.model"]),
            "secure_boot_status": _run(["csrutil", "status"]),
        },
    )


def collect_macos_processes(incident: Incident, *, max_processes: int = 50) -> int:
    """Collect process metadata, excluding command lines and user content."""
    if platform.system().lower() != "darwin":
        return 0
    raw = _run(["ps", "-axo", "pid=,ppid=,comm="], timeout=8)
    count = 0
    for line in raw.splitlines()[:max_processes]:
        parts = line.strip().split(None, 2)
        if len(parts) != 3:
            continue
        pid, ppid, name = parts
        add_event(
            incident,
            event_type="macos_process_observed",
            platform="macos",
            source="local_process_table",
            severity=IncidentSeverity.INFO,
            confidence=1.0,
            data={
                "process_id": pid,
                "parent_process_id": ppid,
                "process_name": name,
            },
        )
        count += 1
    return count


def collect_platform_telemetry(incident: Incident) -> dict[str, int]:
    """Run only collectors appropriate to the current host."""
    system = platform.system().lower()
    counts = {"posture": 0, "events": 0, "processes": 0}
    if system == "windows":
        collect_windows_posture(incident)
        counts["posture"] = 1
        counts["events"] = collect_windows_security_events(incident)
    elif system == "darwin":
        collect_macos_posture(incident)
        counts["posture"] = 1
        counts["processes"] = collect_macos_processes(incident)
    return counts
