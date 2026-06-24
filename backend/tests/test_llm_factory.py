from unittest.mock import MagicMock, patch


def test_get_llm_uses_settings() -> None:
    with patch("app.core.llm.ChatOllama") as mock_cls:
        mock_cls.return_value = MagicMock()
        from app.core.llm import get_llm

        get_llm()
        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        assert kwargs["temperature"] == 0
        assert "model" in kwargs
        assert "base_url" in kwargs
