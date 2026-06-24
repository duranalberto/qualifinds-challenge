from app.domain.workflow import WorkflowExecution, WorkflowPlan


class InMemoryPrototypeStore:
    def __init__(self) -> None:
        self._workflows: list[WorkflowPlan] = []
        self._executions: list[WorkflowExecution] = []

    def save_workflow(self, workflow: WorkflowPlan) -> WorkflowPlan:
        self._workflows.append(workflow)
        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowPlan | None:
        for w in reversed(self._workflows):
            if w.workflow_id == workflow_id:
                return w
        return None

    def list_workflows(
        self, tenant_id: str, limit: int = 10, offset: int = 0
    ) -> list[WorkflowPlan]:
        tenant_workflows = [w for w in reversed(self._workflows) if w.tenant_id == tenant_id]
        return tenant_workflows[offset : offset + limit]

    def count_workflows(self, tenant_id: str) -> int:
        return sum(1 for w in self._workflows if w.tenant_id == tenant_id)

    def save_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        self._executions.append(execution)
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        for e in reversed(self._executions):
            if e.execution_id == execution_id:
                return e
        return None

    def list_executions(
        self, tenant_id: str, limit: int = 10, offset: int = 0
    ) -> list[WorkflowExecution]:
        tenant_execs = [e for e in reversed(self._executions) if e.tenant_id == tenant_id]
        return tenant_execs[offset : offset + limit]

    def count_executions(self, tenant_id: str) -> int:
        return sum(1 for e in self._executions if e.tenant_id == tenant_id)
