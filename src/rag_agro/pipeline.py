"""Orquestra recuperação local, memória da sessão e fallback web opcional."""

import logging
import re
import unicodedata

from rag_agro.config import settings
from rag_agro.generator import (
    INSUFFICIENT_EVIDENCE_MARKER,
    generate,
    generate_with_history,
    generate_with_web_search,
)
from rag_agro.schemas import Answer, RetrievedChunk
from rag_agro.vectorstore import search, search_csv

logger = logging.getLogger(__name__)
History = list[tuple[str, str]]
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
    """Responde uma pergunta isolada, preservando a interface pública existente."""
    return _ask(question, [], k)


def ask_with_history(
    question: str, history: History, k: int | None = None
) -> Answer:
    """Responde considerando o histórico recente fornecido pela sessão do chat."""
    return _ask(question, history, k)


def _ask(question: str, history: History, k: int | None) -> Answer:
    """Executa busca local e só então tenta busca web quando falta evidência."""
    normalized = _normalize(question)
    retrieval_query = _build_retrieval_query(question, history)
    contextual_query = _normalize(retrieval_query)
    report_requested = any(
        term in normalized for term in ("relatorio", "planilha", "excel", "pdf", "exportar")
    )
    is_capability_question = any(term in contextual_query for term in CAPABILITY_TERMS)
    is_csv_request = any(term in contextual_query for term in CSV_TERMS)

    csv_query = question if _has_data_filter(normalized) else retrieval_query
    csv_chunks = search_csv("") if is_capability_question else search_csv(csv_query)
    if is_csv_request and not _has_data_filter(contextual_query):
        csv_chunks = search_csv("")

    semantic_chunks = search(retrieval_query, k)
    chunks = _merge_chunks(semantic_chunks, csv_chunks)
    if not chunks:
        local_answer = (
            "Não encontrei essa informação nos relatórios indexados. "
            "Confira se os arquivos estão em data/raw e execute a indexação."
        )
        return _try_web_fallback(question, chunks, history, report_requested, local_answer)

    if history:
        local_answer = generate_with_history(question, chunks, history)
    else:
        local_answer = generate(question, chunks)

    if local_answer.lstrip().startswith(INSUFFICIENT_EVIDENCE_MARKER):
        return _try_web_fallback(
            question, chunks, history, report_requested, _strip_insufficient_marker(local_answer)
        )
    return Answer(local_answer, chunks, report_requested)


def _try_web_fallback(
    question: str,
    chunks: list[RetrievedChunk],
    history: History,
    report_requested: bool,
    local_answer: str,
) -> Answer:
    """Executa grounding web quando habilitado e trata falhas sem inventar dados."""
    if not settings.web_search_enabled:
        return Answer(local_answer, chunks, report_requested)
    if settings.llm_provider != "gemini":
        message = (
            f"{local_answer}\n\nA busca online está disponível somente com "
            "LLM_PROVIDER=gemini."
        )
        return Answer(message, chunks, report_requested)
    try:
        web_answer, web_sources = generate_with_web_search(question, chunks, history)
    except Exception:
        logger.exception("Falha ao consultar a busca online do Gemini")
        message = f"{local_answer}\n\nA busca online falhou; nenhum dado externo foi acrescentado."
        return Answer(message, chunks, report_requested)
    if web_sources:
        return Answer(web_answer, chunks, report_requested, web_sources)
    if chunks:
        return Answer(local_answer, chunks, report_requested)
    return Answer(web_answer, [], report_requested)


def _strip_insufficient_marker(text: str) -> str:
    """Remove o marcador interno antes de exibir ou exportar a resposta."""
    return text.lstrip()[len(INSUFFICIENT_EVIDENCE_MARKER) :].strip()


def _build_retrieval_query(question: str, history: History) -> str:
    """Acrescenta perguntas anteriores para resolver referências curtas no seguimento."""
    previous_questions = [content for role, content in history if role == "user"][-3:]
    return "\n".join([*previous_questions, question])


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
    """Detecta cultura ou período especificado para não ampliar consulta CSV sem querer."""
    return any(term in question for term in DATA_FILTER_TERMS) or bool(
        re.search(r"\b20\d{2}\b", question)
    )


def _normalize(text: str) -> str:
    """Remove acentos para reconhecer intenções digitadas em português ou espanhol."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
