import json

from evals.run_eval import evaluate_rows, save_results
from rag_agro.schemas import RetrievedChunk


def test_evaluate_rows_calcula_hit_rate_e_mrr_sem_busca_real():
    rows = [
        {"question": "q1", "expected_source": "b.pdf"},
        {"question": "q2", "expected_source": "missing.pdf"},
    ]

    def fake_search(question, _k):
        if question == "q1":
            return [
                RetrievedChunk("irrelevante", "a.pdf", 1, 0.9),
                RetrievedChunk("resposta", "b.pdf", 2, 0.8),
            ]
        return [RetrievedChunk("outro", "c.pdf", 1, 0.7)]

    result = evaluate_rows(rows, 4, fake_search)

    assert result["hits"] == 1
    assert result["hit_rate"] == 0.5
    assert result["mrr"] == 0.25
    assert [item["rank"] for item in result["items"]] == [2, None]


def test_save_results_cria_json_legivel(tmp_path):
    result = {
        "top_k": 4,
        "questions": 1,
        "hits": 1,
        "hit_rate": 1.0,
        "mrr": 1.0,
        "items": [],
    }

    path = save_results(result, tmp_path)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert path.parent == tmp_path
    assert saved["mrr"] == 1.0
    assert saved["top_k"] == 4

