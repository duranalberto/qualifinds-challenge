from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.domain.workflow import IntegrationName


class IntegrationCall(BaseModel):
    tenant_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class IntegrationResult(BaseModel):
    integration: IntegrationName
    action: str
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class IntegrationClient(Protocol):
    integration: IntegrationName

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        """Execute an integration action."""
