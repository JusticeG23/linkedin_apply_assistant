from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    FOUND = "found"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    PACKET_READY = "packet_ready"
    APPLIED = "applied"


@dataclass
class Job:
    job_id: str
    title: str
    company: str
    location: str
    url: str
    source: str = "LinkedIn"
    easy_apply: bool = False
    posted_at: str = ""
    salary_text: str = ""
    work_mode: str = ""
    description: str = ""
    status: JobStatus = JobStatus.FOUND
    score: int = 0
    reject_reason: str = ""
    fit_notes: str = ""
    estimated_tc: Optional[int] = None
    search_preset: str = ""
