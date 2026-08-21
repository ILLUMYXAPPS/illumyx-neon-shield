"""Local-first copyright evidence scanner for ILLUMYX Neon Shield.

The scanner never uploads file contents. It builds SHA-256 fingerprints for
reference files and compares them with a selected target tree. It also records
normalized-name matches and sampled-byte similarity so altered/renamed copies
can be flagged for review without declaring infringement automatically.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Iterable

CHUNK_SIZE = 64 * 1024
SUPPORTED = {
    ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus",
    ".aiff", ".aif", ".mp4", ".mov", ".mkv", ".png", ".jpg", ".jpeg",
    ".webp", ".gif", ".pdf", ".txt", ".md", ".docx", ".zip", ".7z",
}


@dataclass(frozen=True)
class ReferenceFingerprint:
    source: str
    size: int
    sha256: str
    normalized_name: str
    sampled_digest: str


@dataclass(frozen=True)
class ScanMatch:
    source: str
    candidate: str
    match_type: str
    confidence: float
    source_sha256: str
    candidate_sha256: str
    detail: str
    detected_at: str


def _normalized_name(path: Path) -> str:
    stem = path.stem.lower()
    stem = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", stem)
    stem = re.sub(r"[^a-z0-9]+", " ", stem)
    return " ".join(stem.split())


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_digest(path: Path) -> str:
    size = path.stat().st_size
    if size == 0:
        return sha256(b"").hexdigest()
    offsets = sorted({0, max(0, size // 2 - CHUNK_SIZE // 2), max(0, size - CHUNK_SIZE)})
    digest = sha256()
    with path.open("rb") as handle:
        for offset in offsets:
            handle.seek(offset)
            digest.update(handle.read(min(CHUNK_SIZE, size - offset)))
    return digest.hexdigest()


def iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and (path.suffix.lower() in SUPPORTED or not path.suffix):
            yield path


def fingerprint_reference(root: Path) -> list[ReferenceFingerprint]:
    fingerprints: list[ReferenceFingerprint] = []
    for path in iter_files(root):
        try:
            fingerprints.append(
                ReferenceFingerprint(
                    source=str(path),
                    size=path.stat().st_size,
                    sha256=_hash_file(path),
                    normalized_name=_normalized_name(path),
                    sampled_digest=_sample_digest(path),
                )
            )
        except (OSError, PermissionError):
            continue
    return fingerprints


def scan_targets(references: list[ReferenceFingerprint], target_root: Path) -> list[ScanMatch]:
    exact = {item.sha256: item for item in references}
    sampled = {item.sampled_digest: item for item in references}
    names: dict[str, list[ReferenceFingerprint]] = {}
    for item in references:
        if item.normalized_name:
            names.setdefault(item.normalized_name, []).append(item)

    matches: list[ScanMatch] = []
    detected = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for candidate in iter_files(target_root):
        try:
            candidate_sha = _hash_file(candidate)
            candidate_sample = _sample_digest(candidate)
            candidate_name = _normalized_name(candidate)
        except (OSError, PermissionError):
            continue

        ref = exact.get(candidate_sha)
        if ref:
            matches.append(ScanMatch(
                ref.source, str(candidate), "EXACT SHA-256", 100.0,
                ref.sha256, candidate_sha,
                "Byte-for-byte identical file.", detected,
            ))
            continue

        ref = sampled.get(candidate_sample)
        if ref and ref.size == candidate.stat().st_size:
            matches.append(ScanMatch(
                ref.source, str(candidate), "SAMPLED FINGERPRINT", 96.0,
                ref.sha256, candidate_sha,
                "Matching beginning/middle/end byte samples and file size.", detected,
            ))
            continue

        for ref in names.get(candidate_name, []):
            size_ratio = min(ref.size, candidate.stat().st_size) / max(ref.size, candidate.stat().st_size, 1)
            if size_ratio >= 0.85:
                confidence = round(70.0 + (size_ratio - 0.85) / 0.15 * 15.0, 1)
                matches.append(ScanMatch(
                    ref.source, str(candidate), "NORMALIZED NAME + SIZE", confidence,
                    ref.sha256, candidate_sha,
                    "Renamed/relocated candidate with a strongly matching size; manual review required.", detected,
                ))
    return matches


def render_transcript(matches: list[ScanMatch], references_count: int, target: Path) -> str:
    lines = [
        "ILLUMYX NEON SHIELD - COPYRIGHT MATCH TRANSCRIPT",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Reference files fingerprinted: {references_count}",
        f"Target scanned: {target}",
        f"Matches requiring review: {len(matches)}",
        "",
    ]
    if not matches:
        lines.append("NO MATCHES DETECTED.")
        lines.append("No candidate matched the configured fingerprint rules.")
        return "\n".join(lines) + "\n"

    for index, match in enumerate(matches, 1):
        lines.extend([
            f"MATCH #{index} | {match.match_type} | CONFIDENCE {match.confidence:.1f}%",
            f"Source: {match.source}",
            f"Candidate: {match.candidate}",
            f"Source SHA-256: {match.source_sha256}",
            f"Candidate SHA-256: {match.candidate_sha256}",
            f"Detail: {match.detail}",
            f"Detected: {match.detected_at}",
            "Status: CANDIDATE MATCH - VERIFY BEFORE MAKING ANY COPYRIGHT CLAIM",
            "",
        ])
    return "\n".join(lines)
