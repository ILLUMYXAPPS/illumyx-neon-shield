"""Framework-neutral Protection Command Centre state model.

This module is deliberately UI-agnostic. A client can render the same command
centre on iOS, web, or desktop while keeping profile and match logic separate.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from protection_profiles import ProtectionProfile, get_profile


@dataclass(frozen=True)
class DashboardStats:
    protected_files: int = 0
    scans_run: int = 0
    candidates: int = 0
    high_priority: int = 0


@dataclass
class ProtectionDashboard:
    profile_key: str
    stats: DashboardStats = field(default_factory=DashboardStats)
    recent_matches: List[Dict[str, object]] = field(default_factory=list)
    alerts: List[Dict[str, object]] = field(default_factory=list)

    @property
    def profile(self) -> ProtectionProfile:
        return get_profile(self.profile_key)

    def snapshot(self) -> Dict[str, object]:
        """Return a serialisable, UI-ready dashboard snapshot."""
        return {
            "profile": {
                "key": self.profile.key,
                "name": self.profile.name,
                "evidence": list(self.profile.evidence),
            },
            "stats": {
                "protected_files": self.stats.protected_files,
                "scans_run": self.stats.scans_run,
                "candidates": self.stats.candidates,
                "high_priority": self.stats.high_priority,
            },
            "recent_matches": list(self.recent_matches),
            "alerts": list(self.alerts),
        }


def create_dashboard(profile_key: str) -> ProtectionDashboard:
    """Create a command-centre state for a configured protection profile."""
    get_profile(profile_key)  # validate early
    return ProtectionDashboard(profile_key=profile_key)
