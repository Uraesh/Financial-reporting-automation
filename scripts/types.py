"""Shared typed models for the automation workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SourceFile:
    """Represents a source file loaded in memory."""

    filename: str
    content: bytes


class UploadedFileLike(Protocol):
    """Protocol used to type uploaded files from UI frameworks."""

    name: str

    def getvalue(self) -> bytes:
        """Return the binary content."""
        raise NotImplementedError


@dataclass(frozen=True)
class ColumnMapping:
    """Resolved columns used by the pipeline."""

    amount: str
    pme: str
    date: str
    flow: str
    region: str = "region"


@dataclass(frozen=True)
class KpiMetrics:
    """KPI payload displayed in dashboard and report."""

    total_engagements: float
    pme_count: int
    transaction_count: int
    region_count: int
