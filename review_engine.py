"""Controlled review and audit workflow for match candidates."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List


class ReviewStatus(str, Enum):
    NEEDS_REVIEW = "needs_review"
    CONFIRMED_MATCH = "confirmed_match"
    FALSE_POSITIVE = "false_positive"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class AuditEntry:
    candidate_id: str
    previous_status: ReviewStatus
    new_status: ReviewStatus
    reason: str
    timestamp: str


@dataclass
class MatchReview:
    candidate_id: str
    status: ReviewStatus = ReviewStatus.NEEDS_REVIEW
    audit: List[AuditEntry] | None = None

    def __post_init__(self) -> None:
        if self.audit is None:
            self.audit = []

    def decide(self, status: ReviewStatus, reason: str) -> AuditEntry:
        if status == ReviewStatus.NEEDS_REVIEW:
            raise ValueError("A decision must move the review out of needs_review")
        if not reason.strip():
            raise ValueError("A decision reason is required")
        entry = AuditEntry(
            candidate_id=self.candidate_id,
            previous_status=self.status,
            new_status=status,
            reason=reason.strip(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.status = status
        self.audit.append(entry)
        return entry

    def transcript(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status.value,
            "audit": [
                {
                    "previous_status": item.previous_status.value,
                    "new_status": item.new_status.value,
                    "reason": item.reason,
                    "timestamp": item.timestamp,
                }
                for item in self.audit
            ],
        }
