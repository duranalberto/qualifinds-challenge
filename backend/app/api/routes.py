from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import AuthContext, require_auth
from app.domain.workflow import (
    ExecutionRequest,
    WorkflowCreateRequest,
    WorkflowExecution,
    WorkflowPlan,
)
from app.integrations.mocks import build_mock_registry
from app.services.executor import WorkflowExecutor
from app.services.planner import RuleBasedPlanner
from app.services.store import InMemoryPrototypeStore

router = APIRouter()

planner = RuleBasedPlanner()
executor = WorkflowExecutor(connector_registry=build_mock_registry())
store = InMemoryPrototypeStore()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/workflows/plan", response_model=WorkflowPlan)
async def plan_workflow(
    request: WorkflowCreateRequest,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowPlan:
    ensure_tenant_access(request.tenant_id, auth)
    try:
        workflow = await planner.plan(request)
        return store.save_workflow(workflow)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/workflows", response_model=WorkflowPlan)
async def create_workflow(
    request: WorkflowCreateRequest,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowPlan:
    return await plan_workflow(request, auth)


@router.get("/workflows/{workflow_id}", response_model=WorkflowPlan)
async def get_workflow(
    workflow_id: str,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowPlan:
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    ensure_tenant_access(workflow.tenant_id, auth)
    return workflow


@router.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecution)
async def execute_workflow(
    workflow_id: str,
    request: ExecutionRequest,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowExecution:
    ensure_tenant_access(request.tenant_id, auth)
    if workflow_id != request.workflow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path workflow_id does not match request.workflow_id.",
        )

    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    ensure_tenant_access(workflow.tenant_id, auth)

    execution = await executor.execute(workflow, request)
    return store.save_execution(execution)


@router.get("/executions/{execution_id}", response_model=WorkflowExecution)
async def get_execution(
    execution_id: str,
    auth: AuthContext = Depends(require_auth),
) -> WorkflowExecution:
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
