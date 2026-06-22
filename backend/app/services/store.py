from app.domain.workflow import WorkflowExecution, WorkflowPlan


class InMemoryPrototypeStore:
    def __init__(self) -> None:
        self.workflows: dict[str, WorkflowPlan] = {}
        self.executions: dict[str, WorkflowExecution] = {}

    def save_workflow(self, workflow: WorkflowPlan) -> WorkflowPlan:
        self.workflows[workflow.workflow_id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowPlan | None:
        return self.workflows.get(workflow_id)

    def save_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        self.executions[execution.execution_id] = execution
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self.executions.get(execution_id)
