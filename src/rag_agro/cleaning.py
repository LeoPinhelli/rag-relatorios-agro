"""Limpa texto extraído e acrescenta metadados derivados do nome do arquivo."""

import math
import re
from collections import Counter, defaultdict
from pathlib import Path


def clean_pages(pages: list[dict], enabled: bool = True) -> list[dict]:
    """Limpa páginas PDF, preserva registros CSV e adiciona tipo e ano conhecidos."""
    by_source: dict[str, list[dict]] = defaultdict(list)
    for page in pages:
        by_source[page["source"]].append(page)

    cleaned: list[dict] = []
    for source_pages in by_source.values():
        source = source_pages[0]["source"]
        is_pdf = Path(source).suffix.lower() == ".pdf"
        repeated_lines = _repeated_margin_lines(source_pages) if is_pdf and enabled else set()
        derived = _metadata_from_filename(source)
        for page in source_pages:
            if not enabled:
                text = page["text"]
            elif is_pdf:
                text = _clean_pdf_text(page["text"], repeated_lines)
            else:
                text = _normalize_text(page["text"])
            cleaned.append({**page, "text": text, **derived})
    return cleaned


def _repeated_margin_lines(pages: list[dict]) -> set[str]:
    """Encontra linhas curtas repetidas nas margens de várias páginas do mesmo PDF."""
    if len(pages) < 2:
        return set()
    counts: Counter[str] = Counter()
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        margin = set(lines[:3] + lines[-3:])
        counts.update(_normalize_line(line) for line in margin if 3 <= len(line) <= 120)
    threshold = max(2, math.ceil(len(pages) * 0.5))
    return {line for line, count in counts.items() if count >= threshold}


def _clean_pdf_text(text: str, repeated_lines: set[str]) -> str:
    """Remove cabeçalhos/rodapés repetidos e recompõe palavras quebradas por hífen."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    content_indexes = [index for index, line in enumerate(lines) if line.strip()]
    margin_indexes = set(content_indexes[:3] + content_indexes[-3:])
    kept = [
        line
        for index, line in enumerate(lines)
        if not (index in margin_indexes and _normalize_line(line) in repeated_lines)
    ]
    normalized = "\n".join(kept)
    normalized = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", normalized)
    return _normalize_text(normalized)


def _normalize_text(text: str) -> str:
    """Padroniza espaços horizontais e excesso de linhas em branco."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_line(line: str) -> str:
    """Normaliza uma linha para comparar margens entre páginas."""
    return re.sub(r"\s+", " ", line).strip().casefold()


def _metadata_from_filename(source: str) -> dict[str, str | int]:
    """Infere tipo de publicação e ano quando o nome do arquivo permite."""
    name = Path(source).stem.casefold()
    metadata: dict[str, str | int] = {}
    if re.search(r"conab|boletim[-_ ]de[-_ ]safras", name):
        metadata["doc_type"] = "conab"
    elif re.search(r"usda|wasde|wwcb", name):
        metadata["doc_type"] = "usda"
    elif "operaciones_informadas" in name:
        metadata["doc_type"] = "sio_granos"

    year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", name)
    if year_match:
        metadata["year"] = int(year_match.group(1))
    else:
        report_match = re.search(r"(?:wasde|wwcb)[-_ ]?(\d{2})(\d{2})", name)
        if report_match:
            metadata["year"] = 2000 + int(report_match.group(2))
    return metadata
