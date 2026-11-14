import sys
import types

import pytest

from rag_agro import generator
from rag_agro.generator import build_context
from rag_agro.schemas import RetrievedChunk


def test_contexto_inclui_fonte_e_pagina():
    chunks = [RetrievedChunk(text="Soja subiu 3%.", source="conab.pdf", page=4, score=0.9)]
    ctx = build_context(chunks)
    assert 'fonte="conab.pdf"' in ctx
    assert 'pagina="4"' in ctx
    assert "Soja subiu 3%." in ctx


def test_contexto_csv_cita_numero_do_registro():
    chunk = RetrievedChunk(text="Produto: SOJA", source="operaciones.csv", page=3, score=1)
    assert 'registro="3"' in build_context([chunk])


def test_system_prompt_exige_citacoes_e_fallback_sem_evidencia():
    assert "APENAS com base" in generator.SYSTEM_PROMPT
    assert "[arquivo, p. N]" in generator.SYSTEM_PROMPT
    assert "[arquivo, registro N]" in generator.SYSTEM_PROMPT
    assert 'Não encontrei essa informação nos relatórios.' in generator.SYSTEM_PROMPT
    assert generator.INSUFFICIENT_EVIDENCE_MARKER in generator.SYSTEM_PROMPT


def test_prompt_web_orienta_fontes_primarias():
    assert "fontes primárias\noficiais" in generator.WEB_SEARCH_SYSTEM_PROMPT
    assert "sites comerciais" in generator.WEB_SEARCH_SYSTEM_PROMPT


def test_generate_usa_gemini_com_contexto_e_prompt(monkeypatch):
    calls = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(text="A safra cresceu [conab.pdf, p. 4].")

    class FakeClient:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.models = FakeModels()

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_module.Client = FakeClient
    types_module = types.ModuleType("google.genai.types")
    types_module.GenerateContentConfig = lambda **kwargs: kwargs
    genai_module.types = types_module
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
    monkeypatch.setattr(
        generator,
        "settings",
        types.SimpleNamespace(
            llm_provider="gemini", llm_model="gemini-test", gemini_api_key="test-key"
        ),
    )

    chunks = [RetrievedChunk(text="Safra cresceu.", source="conab.pdf", page=4, score=0.9)]
    result = generator.generate("Qual foi a safra?", chunks)

    assert result == "A safra cresceu [conab.pdf, p. 4]."
    assert calls["api_key"] == "test-key"
    assert calls["model"] == "gemini-test"
    assert "<contexto>" in calls["contents"]
    assert "</contexto>\n\nPergunta atual:" in calls["contents"]
    assert calls["config"]["system_instruction"] == generator.SYSTEM_PROMPT


def test_generate_exige_chave_do_provedor(monkeypatch):
    monkeypatch.setattr(
        generator,
        "settings",
        types.SimpleNamespace(llm_provider="gemini", gemini_api_key=None),
    )

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        generator.generate("Pergunta", [])


def test_busca_web_retorna_citacoes_oficiais_e_marcadores(monkeypatch):
    calls = {}
    text = "Estimativa publicada pela Conab."
    candidate = types.SimpleNamespace(
        grounding_metadata=types.SimpleNamespace(
            grounding_chunks=[
                types.SimpleNamespace(
                    web=types.SimpleNamespace(
                        uri="https://www.conab.gov.br/boletim.pdf", title="Boletim Conab"
                    )
                )
            ],
            grounding_supports=[
                types.SimpleNamespace(
                    segment=types.SimpleNamespace(end_index=len(text)),
                    grounding_chunk_indices=[0],
                )
            ],
        )
    )

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(text=text, candidates=[candidate])

    class FakeClient:
        def __init__(self, api_key):
            calls["api_key"] = api_key
            self.models = FakeModels()

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_module.Client = FakeClient
    types_module = types.ModuleType("google.genai.types")
    types_module.GenerateContentConfig = lambda **kwargs: kwargs
    types_module.GoogleSearch = lambda: "google-search"
    types_module.Tool = lambda **kwargs: kwargs
    genai_module.types = types_module
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
    monkeypatch.setattr(
        generator,
        "settings",
        types.SimpleNamespace(
            llm_provider="gemini",
            llm_model="gemini-test",
            gemini_api_key="test-key",
            web_search_allowed_domains=("gov.br", "usda.gov"),
        ),
    )

    answer, sources = generator.generate_with_web_search("Pergunta", [], [])

    assert "[Fonte online 1]" in answer
    assert [(source.title, source.url) for source in sources] == [
        ("Boletim Conab", "https://www.conab.gov.br/boletim.pdf")
    ]
    assert calls["config"]["tools"] == [{"google_search": "google-search"}]


def test_busca_web_descarta_fontes_fora_da_lista_oficial(monkeypatch):
    text = "Dado de fonte não permitida."
    candidate = types.SimpleNamespace(
        grounding_metadata=types.SimpleNamespace(
            grounding_chunks=[
                types.SimpleNamespace(
                    web=types.SimpleNamespace(
                        uri="https://example.com/dados", title="Site não oficial"
                    )
                )
            ],
            grounding_supports=[
                types.SimpleNamespace(
                    segment=types.SimpleNamespace(end_index=len(text)),
                    grounding_chunk_indices=[0],
                )
            ],
        )
    )

    class FakeModels:
        def generate_content(self, **_kwargs):
            return types.SimpleNamespace(text=text, candidates=[candidate])

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")
    genai_module.Client = FakeClient
    types_module = types.ModuleType("google.genai.types")
    types_module.GenerateContentConfig = lambda **kwargs: kwargs
    types_module.GoogleSearch = lambda: "google-search"
    types_module.Tool = lambda **kwargs: kwargs
    genai_module.types = types_module
    google_module.genai = genai_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
    monkeypatch.setattr(
        generator,
        "settings",
        types.SimpleNamespace(
            llm_provider="gemini",
            llm_model="gemini-test",
            gemini_api_key="test-key",
            web_search_allowed_domains=("gov.br", "usda.gov"),
        ),
    )

    answer, sources = generator.generate_with_web_search("Pergunta", [], [])

    assert "não encontrou evidências" in answer
    assert sources == []
