from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.core.security import AuthContext, require_auth
from app.domain.workflow import (
    ExecutionRequest,
    WorkflowCreateRequest,
    WorkflowExecution,
    WorkflowPlan,
)
from app.services.executor import WorkflowExecutor
from app.services.planner_graph import LangGraphPlanner
from app.services.store import InMemoryPrototypeStore

router = APIRouter()


def get_planner(request: Request) -> LangGraphPlanner:
    return request.app.state.planner  # type: ignore[no-any-return]


def get_executor(request: Request) -> WorkflowExecutor:
    return request.app.state.executor  # type: ignore[no-any-return]


def get_store(request: Request) -> InMemoryPrototypeStore:
    return request.app.state.store  # type: ignore[no-any-return]


class PaginatedWorkflows(BaseModel):
    items: list[WorkflowPlan]
    total: int
    limit: int
    offset: int


class PaginatedExecutions(BaseModel):
    items: list[WorkflowExecution]
    total: int
    limit: int
    offset: int


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/workflows/plan", response_model=WorkflowPlan)
async def plan_workflow(
    request: WorkflowCreateRequest,
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowPlan:
    ensure_tenant_access(request.tenant_id, auth)
    planner = get_planner(http_request)
    store = get_store(http_request)
    try:
        workflow = await planner.plan(request)
        return store.save_workflow(workflow)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/workflows", response_model=WorkflowPlan)
async def create_workflow(
    request: WorkflowCreateRequest,
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowPlan:
    return await plan_workflow(request, http_request, auth)


@router.get("/workflows", response_model=PaginatedWorkflows)
async def list_workflows(
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedWorkflows:
    store = get_store(http_request)
    items = store.list_workflows(auth.tenant_id, limit=limit, offset=offset)
    total = store.count_workflows(auth.tenant_id)
    return PaginatedWorkflows(items=items, total=total, limit=limit, offset=offset)


@router.get("/workflows/{workflow_id}", response_model=WorkflowPlan)
async def get_workflow(
    workflow_id: str,
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowPlan:
    store = get_store(http_request)
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    ensure_tenant_access(workflow.tenant_id, auth)
    return workflow


@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecution)
async def execute_workflow(
    workflow_id: str,
    request: ExecutionRequest,
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowExecution:
    ensure_tenant_access(request.tenant_id, auth)
    if workflow_id != request.workflow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path workflow_id does not match request.workflow_id.",
        )
    store = get_store(http_request)
    executor = get_executor(http_request)

    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    ensure_tenant_access(workflow.tenant_id, auth)

    execution = await executor.execute(workflow, request)
    return store.save_execution(execution)


@router.get("/executions", response_model=PaginatedExecutions)
async def list_executions(
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedExecutions:
    store = get_store(http_request)
    items = store.list_executions(auth.tenant_id, limit=limit, offset=offset)
    total = store.count_executions(auth.tenant_id)
    return PaginatedExecutions(items=items, total=total, limit=limit, offset=offset)


@router.get("/executions/{execution_id}", response_model=WorkflowExecution)
async def get_execution(
    execution_id: str,
    http_request: Request,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowExecution:
    store = get_store(http_request)
    execution = store.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found.")
    ensure_tenant_access(execution.tenant_id, auth)
    return execution


def ensure_tenant_access(tenant_id: str, auth: AuthContext) -> None:
    if tenant_id != auth.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated tenant does not match requested tenant.",
        )
