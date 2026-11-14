"""Etapa 2: dividir o texto em trechos com sobreposição.

Corta preferencialmente em quebras de parágrafo ou frase,
para não partir uma ideia no meio.
"""

import hashlib

from rag_agro.schemas import Chunk

SEPARATORS = ["\n\n", "\n", ". ", " "]


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap precisa ser menor que chunk_size")
    text = text.strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            for sep in SEPARATORS:
                cut = window.rfind(sep)
                if cut > chunk_size // 2:
                    end = start + cut + len(sep)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def make_chunks(pages: list[dict], chunk_size: int, overlap: int) -> list[Chunk]:
    """Gera chunks com id determinístico: reindexar não duplica dados."""
    result = []
    for page in pages:
        for i, piece in enumerate(split_text(page["text"], chunk_size, overlap)):
            raw_id = f"{page['source']}-{page['page']}-{i}"
            chunk_id = hashlib.sha1(raw_id.encode()).hexdigest()[:16]
            result.append(
                Chunk(
                    id=chunk_id,
                    text=piece,
                    metadata={
                        "source": page["source"],
                        "page": page["page"],
                        **{
                            key: value
                            for key, value in page.items()
                            if key not in {"text", "source", "page"}
                        },
                    },
                )
            )
    return result
