"""Source interface every job-board adapter implements."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from src.models import JobPosting

USER_AGENT = "jobhunt-copilot/0.1 (+https://github.com/)"
TIMEOUT = 30.0

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace from a job description."""
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[JobPosting]:
        """Fetch postings from this source. Must return [] on any failure, never raise."""
        raise NotImplementedError
