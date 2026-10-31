"""Server-side request evidence capture for Neon Shield.

Captures only security-relevant HTTP responses at an application boundary.
It does not scan, probe, or interact with a remote client's device.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from neon_forensics import (
    IncidentSeverity,
    add_event,
    create_incident,
)

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_ip(value: str | None) -> IPAddress | None:
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _in_networks(address: IPAddress, networks: tuple[Network, ...]) -> bool:
    return any(address.version == network.version and address in network for network in networks)


def resolve_client_ip(
    peer_ip: str | None,
    forwarded_for: str | None = None,
    *,
    trusted_proxy_cidrs: Iterable[str] = (),
) -> tuple[str | None, str]:
    """Resolve the network peer safely; forwarded headers count only via trusted proxies.

    Walk the X-Forwarded-For chain from the right, removing explicitly trusted
    proxies. The first untrusted hop is the best available client address.
    Invalid header entries are ignored. An untrusted direct peer makes the
    entire forwarding header untrusted and it is ignored.
    """
    peer = _parse_ip(peer_ip)
    if peer is None:
        return None, "unavailable"

    try:
        networks = tuple(ipaddress.ip_network(item, strict=False) for item in trusted_proxy_cidrs)
    except ValueError as exc:
        raise ValueError("trusted_proxy_cidrs contains an invalid network") from exc

    if not _in_networks(peer, networks):
        return str(peer), "socket_peer"

    chain = [_parse_ip(item) for item in (forwarded_for or "").split(",")]
    chain = [item for item in chain if item is not None]
    chain.append(peer)

    while len(chain) > 1 and _in_networks(chain[-1], networks):
        chain.pop()

    return str(chain[-1]), "trusted_proxy_chain"


class EvidenceSink(Protocol):
    def append(self, record: Mapping[str, Any]) -> str: ...


class JsonlEvidenceSink:
    """Append-only local JSONL sink with a SHA-256 hash chain.

    For production, place this file on encrypted, access-controlled durable
    storage and periodically anchor the latest hash in an independent system.
    A hash chain is tamper-evident only relative to a trusted saved hash.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._previous_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        previous = "0" * 64
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("previous_hash") != previous:
                    raise ValueError("Evidence chain is broken; refusing to append")
                supplied = record.get("record_hash")
                payload = {key: value for key, value in record.items() if key != "record_hash"}
                canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                expected = hashlib.sha256(canonical).hexdigest()
                if supplied != expected:
                    raise ValueError("Evidence record hash is invalid; refusing to append")
                previous = supplied
        return previous

    def append(self, record: Mapping[str, Any]) -> str:
        with self._lock:
            payload = dict(record)
            payload["previous_hash"] = self._previous_hash
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            record_hash = hashlib.sha256(canonical).hexdigest()
            payload["record_hash"] = record_hash
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(payload, sort_keys=True) + "\n")
                stream.flush()
                import os
                os.fsync(stream.fileno())
            self._previous_hash = record_hash
            return record_hash


class RequestEvidenceRecorder:
    """Convert an observed security HTTP response into a Neon Forensics incident."""

    def __init__(
        self,
        sink: EvidenceSink,
        *,
        destination_domain: str,
        trusted_proxy_cidrs: Iterable[str] = (),
    ) -> None:
        if not destination_domain.strip():
            raise ValueError("destination_domain must be configured")
        self.sink = sink
        self.destination_domain = destination_domain.strip().lower()
        self.trusted_proxy_cidrs = tuple(trusted_proxy_cidrs)

    def record(
        self,
        *,
        peer_ip: str | None,
        forwarded_for: str | None,
        method: str,
        status_code: int,
        user_agent: str = "",
    ) -> str | None:
        if status_code not in (401, 403, 429):
            return None
        source_ip, ip_source = resolve_client_ip(
            peer_ip, forwarded_for, trusted_proxy_cidrs=self.trusted_proxy_cidrs
        )
        if source_ip is None:
            return None

        severity = {
            401: IncidentSeverity.LOW,
            403: IncidentSeverity.MEDIUM,
            429: IncidentSeverity.MEDIUM,
        }[status_code]
        incident = create_incident(severity=severity)
        add_event(
            incident,
            event_type={401: "http_authentication_failure", 403: "http_access_denied",
                        429: "http_rate_limited"}[status_code],
            platform="server",
            source="asgi_response_observer",
            severity=severity,
            confidence=0.95,
            data={
                "source_ip": source_ip,
                "client_ip_source": ip_source,
                "destination_domain": self.destination_domain,
                "request_method": method.upper()[:12],
                "http_status": status_code,
                "user_agent": user_agent[:512],
                "event_timestamp_utc": _utc_now(),
            },
        )
        record = {
            "schema_version": 1,
            "incident_id": incident.incident_id,
            "timestamp_utc": incident.events[0].timestamp_utc,
            "event_type": incident.events[0].event_type,
            "severity": severity.value,
            "confidence": incident.confidence,
            "data": dict(incident.events[0].data),
        }
        return self.sink.append(record)


class NeonShieldEvidenceMiddleware:
    """ASGI middleware that records 401/403/429 responses, without request bodies."""

    def __init__(
        self,
        app: Callable[..., Any],
        recorder: RequestEvidenceRecorder,
        *,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.app = app
        self.recorder = recorder
        self.on_error = on_error or (lambda _error: None)

    async def __call__(self, scope: Mapping[str, Any], receive: Callable[..., Any],
                       send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        client = scope.get("client") or (None, None)
        peer_ip = client[0] if client else None
        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        forwarded_for = headers.get(b"x-forwarded-for", b"").decode("latin-1")
        user_agent = headers.get(b"user-agent", b"").decode("latin-1")
        method = str(scope.get("method", "UNKNOWN"))
        status_code: int | None = None

        async def observed_send(message: Mapping[str, Any]) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 0))
            await send(message)
            if message.get("type") == "http.response.start" and status_code in (401, 403, 429):
                try:
                    self.recorder.record(
                        peer_ip=peer_ip,
                        forwarded_for=forwarded_for,
                        method=method,
                        status_code=status_code,
                        user_agent=user_agent,
                    )
                except Exception as exc:  # evidence failure must not break the protected service
                    self.on_error(exc)

        await self.app(scope, receive, observed_send)
