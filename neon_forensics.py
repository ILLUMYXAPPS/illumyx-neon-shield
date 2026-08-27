"""Neon Forensics core: local-first incident evidence and collection policy.

This module deliberately does not perform remote scanning, credential collection,
or hack-back activity. It provides a small, dependency-free evidence model that
platform collectors can feed with already-authorized observations.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class CollectionClass(str, Enum):
    SAFE_TO_COLLECT = "SAFE_TO_COLLECT"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    DO_NOT_COLLECT = "DO_NOT_COLLECT"
    USER_SUBMITTED = "USER_SUBMITTED"


class IncidentSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    CONTAINED = "contained"
    CLOSED = "closed"


@dataclass(frozen=True)
class FieldPolicy:
    field: str
    classification: CollectionClass
    reason: str
    platforms: tuple[str, ...] = ("ios", "android", "windows", "macos")


@dataclass(frozen=True)
class NeonEvent:
    event_id: str
    incident_id: str
    timestamp_utc: str
    event_type: str
    platform: str
    severity: IncidentSeverity
    source: str
    confidence: float
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    incident_id: str
    source: str
    collected_at_utc: str
    content_type: str
    classification: CollectionClass
    sha256: str
    size_bytes: int
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class Incident:
    incident_id: str
    created_at_utc: str
    severity: IncidentSeverity = IncidentSeverity.INFO
    status: IncidentStatus = IncidentStatus.OPEN
    confidence: float = 0.0
    device_id: str | None = None
    events: list[NeonEvent] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)


SAFE_FIELDS = {
    "platform", "os_version", "os_build", "app_version", "app_build",
    "device_model", "device_family", "architecture", "locale", "timezone",
    "app_install_id", "device_public_key", "scan_id", "event_id", "incident_id",
    "event_timestamp_utc", "event_type", "severity", "detection_rule_id",
    "detection_rule_version", "network_status", "connection_type", "vpn_detected",
    "proxy_detected", "dns_configuration_status", "destination_domain",
    "destination_ip", "destination_port", "source_port", "protocol", "connection_timestamp",
    "connection_duration", "tls_version", "tls_certificate_metadata", "http_status",
    "request_method", "user_agent", "response_size", "login_attempt_id",
    "login_timestamp", "login_success", "authentication_method", "mfa_result",
    "session_id", "session_created", "session_terminated", "account_security_event",
    "evidence_id", "sha256", "algorithm", "created_at", "signed_at", "signature_status",
    "network_type", "connection_state", "interface_state", "dns_configuration",
    "local_ip", "installer_source", "package_integrity", "binary_hash", "security_patch_level",
    "verified_boot_status", "play_protect_status", "screen_lock_enabled",
    "developer_options_status", "usb_debugging_status", "secure_boot_status",
    "tpm_presence", "tpm_version", "bitlocker_status", "firewall_status",
    "windows_defender_status", "update_status", "interface_name", "gateway", "dns_servers",
    "dhcp_state", "process_id", "process_name", "process_path", "process_start_time",
    "process_hash", "parent_process_id", "publisher", "digital_signature_status",
    "service_name", "service_state", "binary_path", "signature_status", "driver_name",
    "version", "load_state", "firewall_change", "defender_event", "suspicious_process",
    "suspicious_network_connection", "code_signature_status", "team_identifier",
    "launch_agent_metadata", "launch_daemon_metadata", "login_item_metadata",
    "system_extension_metadata", "configuration_profile_metadata", "bytes_sent",
    "bytes_received", "source_ip", "coarse_location", "country", "region",
    "approximate_location",
}

CONSENT_FIELDS = {
    "network_flow_metadata", "source_endpoint", "destination_endpoint", "precise_location",
    "selected_directories", "selected_file_contents", "selected_file", "screenshot",
    "screen_recording", "scam_message", "email_export", "browser_name", "browser_version",
    "extension_inventory", "suspicious_download_metadata", "specific_security_registry_keys",
    "startup_entries", "persistence_entries", "security_configuration", "targeted_event_logs",
    "process_events", "file_events", "network_events", "authentication_events",
    "execution_events", "persistence_events", "minidump", "crash_dump", "memory_snapshot",
    "command_line_arguments", "memory_regions", "loaded_modules", "process_handles",
    "malware_samples", "user_selected_file", "user_selected_evidence",
}

DO_NOT_COLLECT_FIELDS = {
    "raw_passwords", "password_manager_contents", "private_messages", "keyboard_input",
    "keystrokes", "microphone_recordings", "camera_recordings", "contacts", "call_contents",
    "sms_contents", "private_photo_library", "private_video_library", "other_app_private_data",
    "authentication_tokens", "cookies_from_other_apps", "private_encryption_keys",
    "browser_password_store", "session_tokens", "credit_card_numbers", "banking_credentials",
    "private_documents", "private_emails", "clipboard_history", "full_browser_history",
    "full_memory_dumps", "other_apps_keychain_secrets", "other_apps_passwords", "full_disk_contents",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(8)}"


def classify_field(field: str) -> CollectionClass:
    """Return the hard policy classification for a field name."""
    if field in DO_NOT_COLLECT_FIELDS:
        return CollectionClass.DO_NOT_COLLECT
    if field in CONSENT_FIELDS:
        return CollectionClass.CONSENT_REQUIRED
    if field in SAFE_FIELDS:
        return CollectionClass.SAFE_TO_COLLECT
    return CollectionClass.DO_NOT_COLLECT


def filter_payload(payload: Mapping[str, Any], *, consent_granted: bool = False,
                   user_submitted: bool = False) -> dict[str, Any]:
    """Apply deny-by-default data policy to an observation payload."""
    accepted: dict[str, Any] = {}
    for key, value in payload.items():
        classification = classify_field(key)
        if classification is CollectionClass.SAFE_TO_COLLECT:
            accepted[key] = value
        elif classification is CollectionClass.CONSENT_REQUIRED and (consent_granted or user_submitted):
            accepted[key] = value
    return accepted


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def create_incident(*, device_id: str | None = None,
                    severity: IncidentSeverity = IncidentSeverity.INFO) -> Incident:
    return Incident(incident_id=new_id("NS"), created_at_utc=utc_now(), severity=severity, device_id=device_id)


def add_event(incident: Incident, *, event_type: str, platform: str,
              source: str, data: Mapping[str, Any] | None = None,
              severity: IncidentSeverity = IncidentSeverity.INFO,
              confidence: float = 0.0, consent_granted: bool = False) -> NeonEvent:
    filtered = filter_payload(data or {}, consent_granted=consent_granted)
    event = NeonEvent(event_id=new_id("EVT"), incident_id=incident.incident_id,
                      timestamp_utc=utc_now(), event_type=event_type, platform=platform,
                      severity=severity, source=source,
                      confidence=max(0.0, min(1.0, confidence)), data=filtered)
    incident.events.append(event)
    incident.confidence = max(incident.confidence, event.confidence)
    if _severity_rank(event.severity) > _severity_rank(incident.severity):
        incident.severity = event.severity
    return event


def add_evidence(incident: Incident, content: bytes, *, source: str,
                 content_type: str, classification: CollectionClass,
                 metadata: Mapping[str, Any] | None = None,
                 consent_granted: bool = False) -> EvidenceItem:
    if classification is CollectionClass.DO_NOT_COLLECT:
        raise PermissionError("DO_NOT_COLLECT evidence is rejected by Neon Shield policy")
    if classification is CollectionClass.CONSENT_REQUIRED and not consent_granted:
        raise PermissionError("Explicit consent is required for this evidence")
    user_submitted = classification is CollectionClass.USER_SUBMITTED
    safe_metadata = filter_payload(metadata or {}, consent_granted=consent_granted, user_submitted=user_submitted)
    item = EvidenceItem(evidence_id=new_id("EVD"), incident_id=incident.incident_id,
                        source=source, collected_at_utc=utc_now(), content_type=content_type,
                        classification=classification, sha256=sha256_bytes(content),
                        size_bytes=len(content), metadata=safe_metadata)
    incident.evidence.append(item)
    return item


def _severity_rank(value: IncidentSeverity) -> int:
    return {IncidentSeverity.INFO: 0, IncidentSeverity.LOW: 1, IncidentSeverity.MEDIUM: 2,
            IncidentSeverity.HIGH: 3, IncidentSeverity.CRITICAL: 4}[value]


def evidence_manifest(incident: Incident) -> dict[str, Any]:
    """Create a deterministic evidence manifest suitable for hashing/signing externally.

    The generated timestamp is export metadata and is deliberately excluded from
    the canonical hash input so regenerating a manifest for the same evidence
    produces the same manifest hash.
    """
    entries = [{"evidence_id": item.evidence_id, "sha256": item.sha256,
                "size_bytes": item.size_bytes, "collected_at_utc": item.collected_at_utc}
               for item in sorted(incident.evidence, key=lambda x: x.evidence_id)]
    canonical_manifest = {"manifest_version": 1, "incident_id": incident.incident_id,
                          "entries": entries}
    canonical = json.dumps(canonical_manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        **canonical_manifest,
        "generated_at_utc": utc_now(),
        "manifest_sha256": sha256_bytes(canonical),
    }


def export_incident(incident: Incident, directory: str | Path) -> Path:
    """Write a local JSON evidence package without uploading anything."""
    root = Path(directory) / incident.incident_id
    root.mkdir(parents=True, exist_ok=True)
    payload = asdict(incident)
    payload["severity"] = incident.severity.value
    payload["status"] = incident.status.value
    payload["events"] = [{**asdict(event), "severity": event.severity.value} for event in incident.events]
    payload["evidence"] = [{**asdict(item), "classification": item.classification.value} for item in incident.evidence]
    (root / "incident.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps(evidence_manifest(incident), indent=2, sort_keys=True), encoding="utf-8")
    return root
