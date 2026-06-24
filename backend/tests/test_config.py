

def test_settings_defaults() -> None:
    from app.core.config import Settings

    s = Settings()
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "llama3.1:8b"


def test_settings_env_overrides(monkeypatch: object) -> None:
    import pytest

    with pytest.MonkeyPatch().context() as mp:
        mp.setenv("OLLAMA_BASE_URL", "http://myhost:11434")
        mp.setenv("OLLAMA_MODEL", "qwen2.5:7b")

        from app.core.config import Settings

        s = Settings()
        assert s.ollama_base_url == "http://myhost:11434"
        assert s.ollama_model == "qwen2.5:7b"
