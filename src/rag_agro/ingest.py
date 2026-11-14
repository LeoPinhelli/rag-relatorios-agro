"""CLI de indexação: python -m rag_agro.ingest data/raw"""

import argparse
import logging
from pathlib import Path

from rag_agro.chunking import make_chunks
from rag_agro.cleaning import clean_pages
from rag_agro.config import settings
from rag_agro.loaders import load_folder
from rag_agro.vectorstore import add_chunks

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa PDFs e CSVs no banco vetorial.")
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()

    pages = load_folder(args.folder)
    pages = clean_pages(pages, enabled=settings.cleaning_enabled)
    if settings.cleaning_enabled:
        log.info("Limpeza ativada; metadados documentais inferidos quando possível")
    else:
        log.info("Limpeza desativada; metadados documentais inferidos quando possível")
    log.info("%d páginas/registros carregados", len(pages))
    chunks = make_chunks(pages, settings.chunk_size, settings.chunk_overlap)
    log.info("%d chunks gerados", len(chunks))
    add_chunks(chunks)
    log.info("Indexação concluída em %s", settings.chroma_dir)


if __name__ == "__main__":
    main()
