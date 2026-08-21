"""Universal protection profiles for Neon Shield.

Profiles describe what a user wants to protect without changing the underlying
match/evidence engine. The profile is configuration only and performs no
remote access or automatic enforcement.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class ProtectionType(str, Enum):
    AUDIO = "audio"
    DOCUMENTS = "documents"
    IMAGES = "images"
    VIDEO = "video"
    PROJECTS = "projects"
    CUSTOM = "custom"


@dataclass(frozen=True)
class ProtectionProfile:
    key: str
    name: str
    description: str
    types: Tuple[ProtectionType, ...]
    evidence: Tuple[str, ...]


PROFILES = {
    "music_audio": ProtectionProfile(
        "music_audio", "Music & Audio", "Protect recordings, podcasts and audio files.",
        (ProtectionType.AUDIO,), ("audio", "metadata", "transcript")),
    "documents": ProtectionProfile(
        "documents", "Documents", "Protect important documents and text files.",
        (ProtectionType.DOCUMENTS,), ("fingerprint", "text", "metadata")),
    "images": ProtectionProfile(
        "images", "Images & Artwork", "Protect photographs, artwork and image files.",
        (ProtectionType.IMAGES,), ("fingerprint", "visual", "metadata")),
    "video": ProtectionProfile(
        "video", "Video", "Protect video files and associated metadata.",
        (ProtectionType.VIDEO,), ("fingerprint", "visual", "audio", "metadata")),
    "projects": ProtectionProfile(
        "projects", "Projects & Code", "Protect project files and source code.",
        (ProtectionType.PROJECTS,), ("fingerprint", "structure", "metadata")),
    "custom": ProtectionProfile(
        "custom", "Custom Files", "Protect a user-selected collection of files.",
        (ProtectionType.CUSTOM,), ("fingerprint", "metadata")),
}


def get_profile(key: str) -> ProtectionProfile:
    """Return a configured profile or raise ValueError for an unknown key."""
    try:
        return PROFILES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown protection profile: {key}") from exc


def list_profiles() -> Tuple[ProtectionProfile, ...]:
    """Return profiles in stable UI order."""
    return tuple(PROFILES.values())
