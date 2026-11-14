"""Orquestra a consulta: busca -> contexto combinado -> resposta do Gemini."""

import re
import unicodedata

from rag_agro.generator import generate
from rag_agro.schemas import Answer, RetrievedChunk
from rag_agro.vectorstore import search, search_csv

CAPABILITY_TERMS = ("quais dados", "que dados", "o que voce pode fornecer", "que informacoes")
CSV_TERMS = ("csv", "sio granos", "sio", "operaciones informadas")
DATA_FILTER_TERMS = (
    "soja", "soy", "soybean", "milho", "maiz", "maize", "corn", "trigo", "wheat",
    "girasol", "sunflower", "janeiro", "enero", "fevereiro", "febrero", "marco",
    "marzo", "abril", "maio", "mayo", "junho", "junio", "julho", "julio", "agosto",
    "setembro", "septiembre", "outubro", "octubre", "novembro", "noviembre", "dezembro",
    "diciembre",
)


def ask(question: str, k: int | None = None) -> Answer:
    """Recupera evidências dos documentos e gera uma resposta contextualizada."""
    normalized = _normalize(question)
    report_requested = any(
        term in normalized for term in ("relatorio", "planilha", "excel", "pdf", "exportar")
    )
    is_capability_question = any(term in normalized for term in CAPABILITY_TERMS)
    is_csv_request = any(term in normalized for term in CSV_TERMS)

    csv_chunks = search_csv("") if is_capability_question else search_csv(question)
    if is_csv_request and not _has_data_filter(normalized):
        csv_chunks = search_csv("")

    semantic_chunks = search(question, k)
    chunks = _merge_chunks(semantic_chunks, csv_chunks)
    if not chunks:
        return Answer(
            "Não encontrei essa informação nos relatórios indexados. Confira se os arquivos "
            "estão em data/raw e execute a indexação.",
            [],
            report_requested,
        )
    return Answer(generate(question, chunks), chunks, report_requested)


def _merge_chunks(*groups: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Combina resultados semânticos e CSV sem repetir o mesmo trecho."""
    merged: list[RetrievedChunk] = []
    seen: set[tuple[str, int, str]] = set()
    for group in groups:
        for chunk in group:
            key = (chunk.source, chunk.page, chunk.text)
            if key not in seen:
                seen.add(key)
                merged.append(chunk)
    return merged


def _has_data_filter(question: str) -> bool:
    """Detecta cultura ou período especificado para não ampliar a consulta sem querer."""
    return any(term in question for term in DATA_FILTER_TERMS) or bool(
        re.search(r"\b20\d{2}\b", question)
    )


def _normalize(text: str) -> str:
    """Remove acentos para reconhecer intenções digitadas em português ou espanhol."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
