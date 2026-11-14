"""Etapa 3: embeddings + banco vetorial (ChromaDB, persistido em disco)."""

import re
import unicodedata

import chromadb
from chromadb.utils import embedding_functions

from rag_agro.config import settings
from rag_agro.schemas import Chunk, RetrievedChunk


def get_collection():
    client = chromadb.PersistentClient(path=settings.chroma_dir)
    embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )
    return client.get_or_create_collection(
        name=settings.collection_name,
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(chunks: list[Chunk], batch_size: int = 100) -> None:
    collection = get_collection()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.upsert(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[c.metadata for c in batch],
        )


def search(query: str, k: int | None = None) -> list[RetrievedChunk]:
    collection = get_collection()
    res = collection.query(query_texts=[query], n_results=k or settings.top_k)
    return [
        RetrievedChunk(
            text=doc,
            source=meta["source"],
            page=int(meta["page"]),
            score=round(1 - dist, 3),
        )
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0], strict=True
        )
    ]


def search_csv(query: str) -> list[RetrievedChunk]:
    """Recupera todos os registros CSV compatíveis com produto e mês/ano pedidos."""
    collection = get_collection()
    result = collection.get(include=["documents", "metadatas"])
    question = _normalize(query)
    product_terms = {
        "SOJA": ("soja", "soy", "soybean"),
        "MAIZ": ("maiz", "maize", "milho", "corn"),
        "TRIGO": ("trigo", "wheat"),
        "GIRASOL": ("girasol", "sunflower"),
    }
    product = next(
        (
            _normalize(term)
            for term, aliases in product_terms.items()
            if any(_normalize(alias) in question for alias in aliases)
        ),
        None,
    )
    month_map = {
        "janeiro": "01", "enero": "01", "fevereiro": "02", "febrero": "02",
        "marco": "03", "marzo": "03", "abril": "04", "maio": "05", "mayo": "05",
        "junho": "06", "junio": "06", "julho": "07", "julio": "07",
        "agosto": "08", "setembro": "09", "septiembre": "09", "outubro": "10",
        "octubre": "10", "novembro": "11", "noviembre": "11", "dezembro": "12",
        "diciembre": "12",
    }
    month = next((num for name, num in month_map.items() if name in question), None)
    if month is None:
        numeric_month = re.search(r"\b(0?[1-9]|1[0-2])/(?:20\d{2})\b", query)
        if numeric_month:
            month = numeric_month.group(1).zfill(2)
    year_match = re.search(r"\b20\d{2}\b", query)
    year = year_match.group(0) if year_match else None
    if query.strip() and not product and not month and not year:
        return []
    records = []
    for doc, meta in zip(
        result.get("documents") or [], result.get("metadatas") or [], strict=True
    ):
        if not meta or not str(meta.get("source", "")).lower().endswith(".csv"):
            continue
        normalized = _normalize(doc)
        if product and product not in normalized:
            continue
        date_match = re.search(
            r"(?:data da operacao|data de concertacao):\s*(\d{2})/(\d{2})/(\d{4})",
            normalized,
        )
        if date_match and (
            (month and date_match.group(2) != month)
            or (year and date_match.group(3) != year)
        ):
            continue
        records.append(RetrievedChunk(doc, meta["source"], int(meta["page"]), 1.0))
    return records


def _normalize(text: str) -> str:
    """Normaliza texto para comparar consultas com CSVs em português ou espanhol."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
