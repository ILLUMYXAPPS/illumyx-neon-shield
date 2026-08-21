"""Device session visibility model for Neon Shield.

This records application-level session metadata. It does not claim OS-level
screen mirroring or network interception capabilities.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass(frozen=True)
class DeviceSession:
    device_id: str
    device_name: str
    recognised: bool
    active: bool
    connection_type: str
    last_seen: str
    location_status: str = "not_shared"
    ip_status: str = "not_recorded"

    @property
    def mirroring_status(self) -> str:
        return "active_session" if self.active else "none_detected"


class DeviceSessionRegistry:
    def __init__(self) -> None:
        self._sessions: List[DeviceSession] = []

    def add_or_update(self, session: DeviceSession) -> None:
        self._sessions = [s for s in self._sessions if s.device_id != session.device_id]
        self._sessions.append(session)

    def active_sessions(self) -> List[DeviceSession]:
        return [s for s in self._sessions if s.active]

    def summary(self) -> List[dict[str, object]]:
        return [
            {
                "device_id": s.device_id,
                "device_name": s.device_name,
                "recognised": s.recognised,
                "active": s.active,
                "connection_type": s.connection_type,
                "last_seen": s.last_seen,
                "location_status": s.location_status,
                "ip_status": s.ip_status,
                "mirroring_status": s.mirroring_status,
            }
            for s in self._sessions
        ]
