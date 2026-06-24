from app.domain.workflow import (
    ExecutionStatus,
    IntegrationName,
    WorkflowExecution,
    WorkflowPlan,
    WorkflowStep,
)


def _plan(workflow_id: str, tenant_id: str) -> WorkflowPlan:
    return WorkflowPlan(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        instruction="A test instruction here.",
        name="Test Workflow",
        steps=[
            WorkflowStep(
                step_id="step_one",
                name="Step One",
                integration=IntegrationName.hubspot,
                action="get_company",
            )
        ],
    )


def _execution(execution_id: str, workflow_id: str, tenant_id: str) -> WorkflowExecution:
    return WorkflowExecution(
        execution_id=execution_id,
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=ExecutionStatus.succeeded,
    )


def test_list_workflows_tenant_isolation() -> None:
    from app.services.store import InMemoryPrototypeStore

    store = InMemoryPrototypeStore()
    for i in range(5):
        store.save_workflow(_plan(f"wf_{i}", "tenant_a"))
    for i in range(2):
        store.save_workflow(_plan(f"wf_b_{i}", "tenant_b"))

    assert len(store.list_workflows("tenant_a")) == 5
    assert len(store.list_workflows("tenant_b")) == 2


def test_list_workflows_pagination() -> None:
    from app.services.store import InMemoryPrototypeStore

    store = InMemoryPrototypeStore()
    for i in range(5):
        store.save_workflow(_plan(f"wf_{i}", "tenant_a"))

    page1 = store.list_workflows("tenant_a", limit=2, offset=0)
    page2 = store.list_workflows("tenant_a", limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].workflow_id != page2[0].workflow_id


def test_list_workflows_empty_store() -> None:
    from app.services.store import InMemoryPrototypeStore

    store = InMemoryPrototypeStore()
    assert store.list_workflows("tenant_a") == []


def test_list_executions_tenant_isolation() -> None:
    from app.services.store import InMemoryPrototypeStore

    store = InMemoryPrototypeStore()
    for i in range(3):
        store.save_execution(_execution(f"exec_{i}", "wf_1", "tenant_a"))
    for i in range(1):
        store.save_execution(_execution(f"exec_b_{i}", "wf_1", "tenant_b"))

    assert len(store.list_executions("tenant_a")) == 3
    assert len(store.list_executions("tenant_b")) == 1


def test_list_executions_empty() -> None:
    from app.services.store import InMemoryPrototypeStore

    store = InMemoryPrototypeStore()
    assert store.list_executions("tenant_a") == []
