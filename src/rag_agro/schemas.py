"""Tipos compartilhados entre as etapas do pipeline."""

from dataclasses import dataclass, field


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    text: str
    source: str
    page: int
    score: float


@dataclass
class Answer:
    text: str
    sources: list[RetrievedChunk]
    report_requested: bool = False
