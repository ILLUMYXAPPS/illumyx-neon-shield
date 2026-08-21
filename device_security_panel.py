"""Command-centre summary for recognised and active device sessions."""

from device_sessions import DeviceSessionRegistry


def build_device_security_panel(registry: DeviceSessionRegistry) -> dict[str, object]:
    sessions = registry.summary()
    return {
        "recognised_devices": sum(1 for s in sessions if s["recognised"]),
        "active_sessions": sum(1 for s in sessions if s["active"]),
        "unknown_devices": sum(1 for s in sessions if not s["recognised"]),
        "sessions": sessions,
        "actions": ["view", "verify", "revoke_session"],
    }
