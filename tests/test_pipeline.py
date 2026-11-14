from rag_agro import pipeline
from rag_agro.generator import INSUFFICIENT_EVIDENCE_MARKER
from rag_agro.schemas import Answer, RetrievedChunk, WebSource


def test_ask_combina_pdf_e_csv_e_encaminha_pergunta_ao_gerador(monkeypatch):
    pdf_chunks = [RetrievedChunk("Projeção no relatório.", "conab.pdf", 10, 0.9)]
    csv_chunks = [RetrievedChunk("Operação de soja.", "operaciones.csv", 2, 1.0)]
    generated = {}

    monkeypatch.setattr(pipeline, "search", lambda _query, _k: pdf_chunks)
    monkeypatch.setattr(pipeline, "search_csv", lambda _query: csv_chunks)

    def fake_generate(question, chunks):
        generated["question"] = question
        generated["chunks"] = chunks
        return "Resposta construída pelo Gemini."

    monkeypatch.setattr(pipeline, "generate", fake_generate)
    answer = pipeline.ask("Compare os dados de soja e a projeção")

    assert answer.text == "Resposta construída pelo Gemini."
    assert answer.sources == pdf_chunks + csv_chunks
    assert generated == {
        "question": "Compare os dados de soja e a projeção",
        "chunks": answer.sources,
    }
    assert isinstance(answer, Answer)


def test_pergunta_de_capacidade_tambem_e_respondida_pelo_gerador(monkeypatch):
    all_csv = [RetrievedChunk("Produto: SOJA", "operaciones.csv", 1, 1.0)]
    calls = []
    monkeypatch.setattr(pipeline, "search", lambda _query, _k: [])
    monkeypatch.setattr(
        pipeline, "search_csv", lambda query: all_csv if query == "" else []
    )
    monkeypatch.setattr(
        pipeline,
        "generate",
        lambda question, chunks: calls.append((question, chunks)) or "Resposta do Gemini.",
    )

    answer = pipeline.ask("Quais dados você pode fornecer?")

    assert answer.text == "Resposta do Gemini."
    assert calls == [("Quais dados você pode fornecer?", all_csv)]


def test_pedido_do_csv_retorna_todos_os_registros_ao_gerador(monkeypatch):
    all_csv = [
        RetrievedChunk("Produto: SOJA", "operaciones.csv", 1, 1.0),
        RetrievedChunk("Produto: MAIZ", "operaciones.csv", 2, 1.0),
    ]
    calls = []

    def fake_search_csv(query):
        calls.append(query)
        return all_csv if not query else []

    monkeypatch.setattr(pipeline, "search", lambda _query, _k: [])
    monkeypatch.setattr(pipeline, "search_csv", fake_search_csv)
    monkeypatch.setattr(
        pipeline,
        "generate",
        lambda _question, chunks: f"Linhas recebidas: {len(chunks)}",
    )

    answer = pipeline.ask("Entregue os dados do CSV do SIO Granos")

    assert calls == ["Entregue os dados do CSV do SIO Granos", ""]
    assert answer.text == "Linhas recebidas: 2"
    assert answer.report_requested is False


def test_consulta_sem_fonte_retorna_aviso_sem_chamar_gerador(monkeypatch):
    monkeypatch.setattr(pipeline, "search", lambda _query, _k: [])
    monkeypatch.setattr(pipeline, "search_csv", lambda _query: [])
    monkeypatch.setattr(
        pipeline, "settings", type("Settings", (), {"web_search_enabled": False})()
    )
    monkeypatch.setattr(
        pipeline, "generate", lambda *_args: (_ for _ in ()).throw(AssertionError("LLM chamado"))
    )

    answer = pipeline.ask("Pergunta sem fonte")

    assert "Não encontrei" in answer.text
    assert answer.sources == []


def test_ask_with_history_usa_perguntas_anteriores_na_busca(monkeypatch):
    history = [("user", "Qual a estimativa da soja?"), ("assistant", "Resposta anterior.")]
    calls = {}
    csv_queries = []
    chunk = RetrievedChunk("Projeção de soja e milho.", "boletim.pdf", 9, 0.8)

    def fake_search(query, _k):
        calls["query"] = query
        return [chunk]

    monkeypatch.setattr(pipeline, "search", fake_search)
    monkeypatch.setattr(
        pipeline, "search_csv", lambda query: csv_queries.append(query) or []
    )
    monkeypatch.setattr(
        pipeline,
        "generate_with_history",
        lambda question, chunks, prior: calls.update(
            question=question, chunks=chunks, history=prior
        )
        or "Resposta contextualizada.",
    )

    answer = pipeline.ask_with_history("E o milho?", history)

    assert "Qual a estimativa da soja?" in calls["query"]
    assert "E o milho?" in calls["query"]
    assert calls["question"] == "E o milho?"
    assert calls["history"] == history
    assert calls["chunks"] == [chunk]
    assert csv_queries == ["E o milho?"]
    assert answer.text == "Resposta contextualizada."


def test_busca_online_e_chamada_quando_contexto_local_e_insuficiente(monkeypatch):
    local_chunk = RetrievedChunk("Trecho não responde à pergunta.", "boletim.pdf", 3, 0.7)
    online_source = WebSource("Conab", "https://www.conab.gov.br/relatorio.pdf")
    calls = []
    monkeypatch.setattr(pipeline, "search", lambda _query, _k: [local_chunk])
    monkeypatch.setattr(pipeline, "search_csv", lambda _query: [])
    monkeypatch.setattr(
        pipeline,
        "generate",
        lambda _question, _chunks: f"{INSUFFICIENT_EVIDENCE_MARKER}\nFalta o dado.",
    )
    monkeypatch.setattr(
        pipeline,
        "settings",
        type("Settings", (), {"web_search_enabled": True, "llm_provider": "gemini"})(),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_with_web_search",
        lambda question, chunks, history: calls.append((question, chunks, history))
        or ("Dado publicado. [Fonte online 1]", [online_source]),
    )

    answer = pipeline.ask("Qual o dado atual?")

    assert answer.text == "Dado publicado. [Fonte online 1]"
    assert answer.sources == [local_chunk]
    assert answer.web_sources == [online_source]
    assert calls == [("Qual o dado atual?", [local_chunk], [])]


def test_sem_documentos_tenta_busca_online_se_habilitada(monkeypatch):
    online_source = WebSource("USDA", "https://www.usda.gov/report.pdf")
    monkeypatch.setattr(pipeline, "search", lambda _query, _k: [])
    monkeypatch.setattr(pipeline, "search_csv", lambda _query: [])
    monkeypatch.setattr(
        pipeline,
        "settings",
        type("Settings", (), {"web_search_enabled": True, "llm_provider": "gemini"})(),
    )
    monkeypatch.setattr(
        pipeline,
        "generate_with_web_search",
        lambda *_args: ("Resposta baseada na web [Fonte online 1].", [online_source]),
    )

    answer = pipeline.ask("Qual a estimativa mais recente?")

    assert answer.sources == []
    assert answer.web_sources == [online_source]
