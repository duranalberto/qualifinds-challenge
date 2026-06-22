from typing import Annotated

from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings


class AuthContext(BaseModel):
    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)


async def require_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_tenant_id: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> AuthContext:
    expected = f"Bearer {settings.auth_demo_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token.",
        )
    if not x_tenant_id or not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id and X-User-Id headers are required.",
        )
    return AuthContext(tenant_id=x_tenant_id, user_id=x_user_id)
