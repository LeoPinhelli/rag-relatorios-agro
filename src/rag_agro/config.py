"""Configuração central. Tudo vem do .env, nada fica fixo no código."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    chroma_dir: str = os.getenv("CHROMA_DIR", ".chroma")
    collection_name: str = os.getenv("COLLECTION_NAME", "relatorios_agro")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "4"))


settings = Settings()
