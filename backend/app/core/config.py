from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "sqlite+aiosqlite:///./workflow_challenge.db"
    auth_demo_token: str = "demo-token"
    cors_allowed_origins: list[str] = [
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ]
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
