import importlib

import rag_agro.config as config


def test_settings_le_configuracoes_do_ambiente(monkeypatch):
    original_settings = config.settings
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")
    monkeypatch.setenv("CHUNK_SIZE", "1234")
    try:
        reloaded = importlib.reload(config)
        assert reloaded.settings.llm_model == "gemini-test-model"
        assert reloaded.settings.chunk_size == 1234
    finally:
        config.settings = original_settings
