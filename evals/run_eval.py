"""Avalia recuperação por hit rate@k e MRR, sem chamar o LLM."""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from rag_agro.config import settings
from rag_agro.schemas import RetrievedChunk
from rag_agro.vectorstore import search

EVALS_DIR = Path(__file__).parent
DATASET = EVALS_DIR / "dataset.jsonl"
RESULTS_DIR = EVALS_DIR / "results"
SearchFunction = Callable[[str, int], list[RetrievedChunk]]


def evaluate_rows(
    rows: list[dict], k: int, search_fn: SearchFunction = search
) -> dict:
    """Calcula hit rate@k, posição da fonte esperada e MRR para cada pergunta."""
    items = []
    for row in rows:
        retrieved = search_fn(row["question"], k)
        rank = next(
            (
                position
                for position, chunk in enumerate(retrieved, start=1)
                if chunk.source == row["expected_source"]
            ),
            None,
        )
        items.append(
            {
                "question": row["question"],
                "expected_source": row["expected_source"],
                "rank": rank,
                "reciprocal_rank": 1 / rank if rank else 0.0,
                "retrieved": [
                    {"source": chunk.source, "page": chunk.page, "score": chunk.score}
                    for chunk in retrieved
                ],
            }
        )

    total = len(items)
    hits = sum(item["rank"] is not None for item in items)
    mrr = sum(item["reciprocal_rank"] for item in items) / total if total else 0.0
    return {
        "top_k": k,
        "questions": total,
        "hits": hits,
        "hit_rate": hits / total if total else 0.0,
        "mrr": mrr,
        "items": items,
    }


def save_results(result: dict, results_dir: Path = RESULTS_DIR) -> Path:
    """Salva métricas e fontes recuperadas em JSON com a data local."""
    results_dir.mkdir(parents=True, exist_ok=True)
    run_date = datetime.now().astimezone().date().isoformat()
    output_path = results_dir / f"{run_date}.json"
    payload = {
        "date": run_date,
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        **result,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output_path


def main() -> None:
    """Executa a avaliação local e imprime as métricas agregadas."""
    rows = [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = evaluate_rows(rows, settings.top_k)
    output_path = save_results(result)
    print(
        f"Hit rate@{result['top_k']}: {result['hits']}/{result['questions']} "
        f"= {result['hit_rate']:.1%}"
    )
    print(f"MRR: {result['mrr']:.3f}")
    for item in result["items"]:
        rank = item["rank"] if item["rank"] is not None else "não encontrado"
        print(f"Posição {rank}: {item['question']}")
    print(f"Resultado salvo em {output_path}")


if __name__ == "__main__":
    main()
