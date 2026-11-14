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
    assert "</contexto>\n\nPergunta:" in calls["contents"]
    assert calls["config"]["system_instruction"] == generator.SYSTEM_PROMPT


def test_generate_exige_chave_do_provedor(monkeypatch):
    monkeypatch.setattr(
        generator,
        "settings",
        types.SimpleNamespace(llm_provider="gemini", gemini_api_key=None),
    )

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        generator.generate("Pergunta", [])
