"""Local, read-only network telemetry for Neon Forensics.

Windows implementation reads existing WFP Security events only. It does not
change audit policy, install filters, capture packets, or inspect payloads.
Other platforms return an empty result until a platform-native collector is
implemented.
"""
from __future__ import annotations

import platform
import socket
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional


@dataclass(frozen=True)
class NetworkEvent:
    timestamp_utc: str
    platform: str
    event_type: str
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_ip: Optional[str] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = None
    action: Optional[str] = None
    application: Optional[str] = None
    event_id: Optional[int] = None
    collection_source: str = "local_os_security_log"

    def to_dict(self):
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_data(event: ET.Element, name: str) -> Optional[str]:
    for node in event.findall('.//{*}EventData/{*}Data'):
        if node.attrib.get('Name') == name:
            return node.text
    return None


def _protocol(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return {6: "TCP", 17: "UDP", "6": "TCP", "17": "UDP"}.get(value, value)


def collect_windows_wfp_events(max_events: int = 100) -> List[NetworkEvent]:
    """Read existing Windows WFP connection audit events.

    Event IDs 5156/5157 represent permitted/blocked connections. The
    collector intentionally does not enable auditing or modify firewall/WFP
    configuration. If auditing is disabled, no network events are returned.
    """
    if platform.system() != "Windows":
        return []
    query = (
        '*[System[(EventID=5156 or EventID=5157)]]'
    )
    command = [
        "wevtutil", "qe", "Security", "/q:" + query,
        "/f:xml", f"/c:{max_events}", "/rd:true"
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=8, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    try:
        root = ET.fromstring(
            "<Events>" + completed.stdout.replace("</Event>", "</Event><Event>", 0) + "</Events>"
        )
    except ET.ParseError:
        # wevtutil may return multiple top-level Event elements; parse them
        # independently rather than failing the entire scan.
        events = []
        chunks = completed.stdout.split("<Event ")
        for chunk in chunks[1:]:
            xml = "<Event " + chunk
            if "</Event>" not in xml:
                continue
            xml = xml.split("</Event>", 1)[0] + "</Event>"
            try:
                events.append(ET.fromstring(xml))
            except ET.ParseError:
                continue
        return _parse_wfp_events(events)
    return _parse_wfp_events(root.findall('.//{*}Event'))


def _parse_wfp_events(events) -> List[NetworkEvent]:
    result = []
    for event in events:
        event_id_node = event.find('.//{*}System/{*}EventID')
        try:
            event_id = int(event_id_node.text) if event_id_node is not None else None
        except (TypeError, ValueError):
            event_id = None
        timestamp = event.find('.//{*}System/{*}TimeCreated')
        timestamp_utc = (timestamp.attrib.get('SystemTime') if timestamp is not None else None) or _utc_now()
        result.append(NetworkEvent(
            timestamp_utc=timestamp_utc,
            platform="windows",
            event_type="network_connection",
            source_ip=_event_data(event, "SourceAddress"),
            source_port=_safe_int(_event_data(event, "SourcePort")),
            destination_ip=_event_data(event, "DestAddress"),
            destination_port=_safe_int(_event_data(event, "DestPort")),
            protocol=_protocol(_event_data(event, "Protocol")),
            action="allowed" if event_id == 5156 else "blocked" if event_id == 5157 else None,
            application=_event_data(event, "ApplicationName"),
            event_id=event_id,
        ))
    return result


def _safe_int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def collect_network_events(max_events: int = 100) -> List[NetworkEvent]:
    """Platform dispatcher. Never enables auditing or captures payloads."""
    if platform.system() == "Windows":
        return collect_windows_wfp_events(max_events=max_events)
    return []
