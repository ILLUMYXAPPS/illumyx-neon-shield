"""Observation-only Windows Filtering Platform telemetry.

Reads already-recorded Security events 5156/5157. It never enables auditing,
changes firewall policy, installs filters, captures packets, or inspects payloads.
"""
from __future__ import annotations

import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from typing import Callable

from neon_forensics import Incident, IncidentSeverity, add_event


def _run_wevtutil(command: list[str], timeout: int = 12) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _event_values(xml_text: str) -> dict[str, str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}
    values: dict[str, str] = {}
    for node in root.iter():
        if node.tag.endswith("Data") and node.attrib.get("Name"):
            values[node.attrib["Name"]] = (node.text or "").strip()
    return values


def _event_id(xml_text: str) -> str | None:
    match = re.search(r"<EventID[^>]*>(\d+)</EventID>", xml_text)
    return match.group(1) if match else None


def collect_windows_wfp_events(
    incident: Incident,
    *,
    max_events: int = 50,
    runner: Callable[[list[str], int], str] = _run_wevtutil,
) -> int:
    """Collect existing WFP connection audit events 5156 and 5157."""
    if platform.system().lower() != "windows":
        return 0

    query = "*[System[(EventID=5156 or EventID=5157)]]"
    raw = runner(
        ["wevtutil", "qe", "Security", "/q:" + query, "/f:RenderedXml", "/c:" + str(max_events)],
        12,
    )
    if not raw:
        return 0

    chunks = re.findall(r"<Event[\s\S]*?</Event>", raw)
    count = 0
    for xml_text in chunks:
        eid = _event_id(xml_text)
        if eid not in {"5156", "5157"}:
            continue
        values = _event_values(xml_text)
        data = {
            "event_id": eid,
            "source_ip": values.get("SourceAddress", ""),
            "destination_ip": values.get("DestAddress", ""),
            "source_port": values.get("SourcePort", ""),
            "destination_port": values.get("DestPort", ""),
            "protocol": values.get("Protocol", ""),
            "process_id": values.get("ProcessID", ""),
            "process_path": values.get("Application", ""),
        }
        severity = IncidentSeverity.MEDIUM if eid == "5157" else IncidentSeverity.INFO
        add_event(
            incident,
            event_type="windows_wfp_connection_blocked" if eid == "5157" else "windows_wfp_connection_allowed",
            platform="windows",
            source="windows_wfp_security_log",
            severity=severity,
            confidence=1.0,
            data=data,
        )
        count += 1
    return count
