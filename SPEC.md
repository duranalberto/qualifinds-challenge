# Spec-Driven Development: AI Workflow MVP Enhancement

## 1. Framework Decision

### Why LangGraph

| Criterion | LangChain | LangGraph | CrewAI | Raw Ollama SDK |
|---|---|---|---|---|
| Sequential agent nodes | Via chains | Native (linear edges) | Multi-agent (overkill) | Manual |
| Ollama support | `ChatOllama` | `ChatOllama` (inherits) | Limited | Native |
| Typed state between nodes | No | Yes (`TypedDict`) | No | No |
| Structured output (Pydantic) | `.with_structured_output()` | `.with_structured_output()` | No | No |
| Independently testable nodes | Partial | Yes | No | N/A |
| Retry / error handling | Manual | Built-in | Built-in | Manual |

**Decision: LangGraph** with `langchain-ollama`.

LangGraph models each planning stage as a discrete, stateful node connected by directed edges. Sequential execution is the default when edges are added linearly (`START → A → B → C → END`). No parallel node execution is used in this MVP. The LLM is called in **exactly one node** (`extract_intent`). All other nodes are pure Python business logic — deterministic, fast, and testable without an Ollama instance.

### Ollama Model

| Model | Size | Tool Calling | Recommended Use |
|---|---|---|---|
| `llama3.1:8b` | 4.7 GB | Yes | **Primary** — best structured output locally |
| `qwen2.5:7b` | 4.4 GB | Yes | Alternative if llama3.1 unavailable |
| `mistral:7b-instruct` | 4.1 GB | Partial | Fallback |

Pull before running: `ollama pull llama3.1:8b`

---

## 2. Architecture Overview

```
User Instruction
      │
      ▼
┌─────────────────────────────────────────────┐
│           LangGraph Planner                  │
│                                              │
│  [extract_intent]  ← LLM call (1x)          │
│        │                                     │
│  [select_template] ← business logic          │
│        │                                     │
│  [fill_parameters] ← business logic          │
│        │                                     │
│  [validate_steps]  ← business logic          │
└─────────────────┬───────────────────────────┘
                  │ WorkflowPlan
                  ▼
        ┌──────────────────┐
        │  WorkflowExecutor │
        │                  │
        │  step 1 (seq)    │ ← SafeConditionEvaluator
        │  step 2 (seq)    │ ← resolve_payload + retry
        │  step 3 (seq)    │
        └──────────────────┘
                  │
         WorkflowExecution (with timing)
```

**Sequential contract:** LangGraph nodes run one at a time. Executor steps run one at a time. No `asyncio.gather` across nodes or steps.

---

## 3. New Dependency Stack

```toml
# pyproject.toml additions
"langgraph>=0.2.0",
"langchain-ollama>=0.2.0",
"langchain-core>=0.3.0",
"simpleeval>=0.9.13",
```

New env var: `OLLAMA_BASE_URL` (default `http://localhost:11434`), `OLLAMA_MODEL` (default `llama3.1:8b`).

> **Docker / Ollama setup:** Ollama runs on the **host machine**, not as a compose service (GPU pass-through and 4.7 GB model pulls make it impractical as a sidecar). Before `docker compose up --build`, run:
> ```bash
> ollama pull llama3.1:8b   # one-time, ~4.7 GB
> ollama serve               # if not already running as a system service
> ```
> In `docker-compose.yml`, set `OLLAMA_BASE_URL=http://host.docker.internal:11434` so the backend container reaches the host Ollama instance. On Linux, replace `host.docker.internal` with the host's bridge IP (typically `172.17.0.1`) or add `--network=host`. If Ollama is unreachable at startup, the graph continues with `intent=None` and template defaults (see TICK-014 acceptance criteria) — the stack will not crash.

---

## 4. Intent Schema (LLM Output Contract)

The LLM is asked to return this structure. All other nodes consume it.

```python
class DetectedThreshold(BaseModel):
    field: str        # "employee_count", "annual_revenue", "risk_score"
    operator: Literal[">", "<", ">=", "<=", "==", "!="]
    value: float | str

class ExtractedIntent(BaseModel):
    trigger_type: str          # "new_lead", "deal_closed", "account_updated",
                               # "invoice_created", "support_ticket", "unknown"
    integrations: list[str]    # ["hubspot", "sap", "slack"] — mentioned explicitly
    action_intents: list[str]  # ["enrich", "notify", "create_task", "escalate",
                               # "update_stage", "create_issue", "assign"]
    threshold: DetectedThreshold | None
    workflow_name: str         # human-readable, e.g. "Large Lead Enrichment"
```

---

## 5. Workflow Template Registry

Five named templates. Each template is a function that receives `ExtractedIntent` and returns `list[WorkflowStep]`.

| Template ID | Trigger | Default Integrations | Steps |
|---|---|---|---|
| `large_lead_enrichment` | `new_lead` + threshold | hubspot, sap, slack | get_company → enrich → create_task → notify |
| `deal_closed_processing` | `deal_closed` | salesforce, sap, jira, slack | get_account → check_compliance → create_issue → notify |
| `high_risk_account_alert` | `account_updated` | hubspot OR salesforce, sap, slack | get_company → check_compliance → escalate_ticket → notify |
| `churn_risk_response` | `support_ticket` | zendesk, hubspot, slack | get_ticket → get_contacts → assign_ticket → send_dm |
| `enterprise_onboarding` | `new_lead` (no threshold or large) | hubspot, jira, slack | get_company → create_deal → create_issue → notify |

Template selection priority:
1. Match `trigger_type` to template
2. If `threshold` present and `trigger_type == new_lead` → `large_lead_enrichment`
3. Override step integrations with `integrations` from intent if a compatible action exists
4. Fall back to `large_lead_enrichment` if no match

---

## 6. Epics & Tickets

---

### EPIC-1: Infrastructure & Dependencies

---

#### TICK-001 — Add LangGraph and Ollama dependencies

**What:** Add `langgraph`, `langchain-ollama`, `langchain-core`, `simpleeval` to `pyproject.toml` dependencies.

**Files:** `backend/pyproject.toml`

**Acceptance criteria:**
- `pip install -e ".[dev]"` installs without conflicts
- `from langgraph.graph import StateGraph` imports successfully
- `from langchain_ollama import ChatOllama` imports successfully
- `from simpleeval import EvalWithCompoundTypes` imports successfully

**Test:** `tests/test_imports.py` — assert all four imports succeed.

---

#### TICK-002 — Add Ollama settings to config

**What:** Extend `Settings` with `ollama_base_url: str` and `ollama_model: str`.

**Files:** `backend/app/core/config.py`

**Acceptance criteria:**
- `Settings()` defaults to `ollama_base_url="http://localhost:11434"` and `ollama_model="llama3.1:8b"`
- Both values are overridable via environment variables `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
- `docker-compose.yml` exposes these env vars; the default value for `OLLAMA_BASE_URL` in compose is `http://host.docker.internal:11434` (Mac/Windows) so the backend container can reach the host-running Ollama instance. Local dev outside Docker continues to use `http://localhost:11434`.

**Test:** `tests/test_config.py` — instantiate `Settings` with env overrides and assert values.

---

#### TICK-003 — LLM factory

**What:** Create `backend/app/core/llm.py` with a `get_llm()` function that returns a `ChatOllama` instance configured from `settings`.

**Files:** `backend/app/core/llm.py` (new)

**Acceptance criteria:**
- `get_llm()` returns a `ChatOllama` with `model=settings.ollama_model` and `base_url=settings.ollama_base_url`
- `temperature` is set to `0` (deterministic output)
- The function is importable and does not make any network calls at import time

**Test:** `tests/test_llm_factory.py` — mock `ChatOllama` and assert `get_llm()` passes correct args.

---

### EPIC-2: Domain Model Enhancements

---

#### TICK-004 — Add `name` field to `WorkflowPlan`

**What:** Add `name: str = Field(min_length=1)` to `WorkflowPlan`. Update all planner code that constructs `WorkflowPlan`.

**Files:** `backend/app/domain/workflow.py`, `backend/app/services/planner.py`

**Acceptance criteria:**
- `WorkflowPlan` requires a non-empty `name`
- Existing `RuleBasedPlanner` sets `name="Rule-Based Workflow"` as placeholder
- `GET /workflows/{workflow_id}` response includes `name`
- `POST /workflows/plan` response includes `name`

**Test:** `tests/test_workflow_models.py` — assert `WorkflowPlan` with missing `name` raises `ValidationError`. Assert existing plan factory test still passes with name field present.

---

#### TICK-005 — Add timing fields to `StepExecutionResult`

**What:** Add `started_at: datetime | None`, `completed_at: datetime | None`, `duration_ms: int | None` to `StepExecutionResult`.

**Files:** `backend/app/domain/workflow.py`

**Acceptance criteria:**
- All three fields are optional (default `None`) so existing tests pass without changes
- Fields serialize to ISO 8601 strings in JSON responses
- Fields are populated by the executor (TICK-016)

**Test:** `tests/test_workflow_models.py` — assert `StepExecutionResult` serializes timing fields correctly when populated; assert model is valid with all-None timing fields.

---

#### TICK-006 — Add `RetryConfig` and `retry` field to `WorkflowStep`

**What:** Create `RetryConfig(BaseModel)` with `max_attempts: int = 2` and `delay_ms: int = 500`. Add `retry: RetryConfig | None = None` to `WorkflowStep`.

**Files:** `backend/app/domain/workflow.py`

**Acceptance criteria:**
- `WorkflowStep` accepts optional `retry` field
- `RetryConfig` validates `max_attempts >= 1` and `delay_ms >= 0`
- Existing steps without `retry` behave identically (no retries)

**Test:** `tests/test_workflow_models.py` — assert `RetryConfig(max_attempts=0)` raises `ValidationError`. Assert step without retry serializes without `retry` key in JSON.

---

#### TICK-007 — Add `duration_ms` and `started_at` to `WorkflowExecution`

**What:** Add `duration_ms: int | None = None` and `started_at: datetime | None = None` to `WorkflowExecution`.

**Files:** `backend/app/domain/workflow.py`

**Acceptance criteria:**
- Fields are optional, default `None`
- Executor populates them (TICK-019)
- API responses include them

**Test:** `tests/test_workflow_models.py` — round-trip serialization with and without timing fields.

---

### EPIC-3: LangGraph Planner

---

#### TICK-008 — Define `PlannerState` TypedDict

**What:** Create `backend/app/services/planner_state.py` with `PlannerState` and `ExtractedIntent` / `DetectedThreshold` Pydantic models as defined in Section 4.

**Files:** `backend/app/services/planner_state.py` (new)

```python
class PlannerState(TypedDict):
    instruction: str
    tenant_id: str
    intent: ExtractedIntent | None
    template_id: str | None
    steps: list[WorkflowStep]
    validation_errors: list[str]
    workflow_name: str
```

**Acceptance criteria:**
- `PlannerState` is a valid `TypedDict` importable from the module
- `ExtractedIntent` and `DetectedThreshold` are valid Pydantic v2 models
- `ExtractedIntent` fields match Section 4 exactly
- Module has no side effects on import (no LLM calls, no network)

**Test:** `tests/test_planner_state.py` — assert `ExtractedIntent` validates correctly with all trigger types. Assert `DetectedThreshold(operator="?", ...)` raises `ValidationError` (enforced by the `Literal` type). Assert `PlannerState` can be constructed as a plain dict.

---

#### TICK-009 — Implement `extract_intent` node

**What:** Create `backend/app/services/nodes/extract_intent.py`. This is the only node that calls the LLM.

The node calls `llm.with_structured_output(ExtractedIntent)` with a system prompt listing available trigger types, integrations, and action intents. Returns updated state with `intent` populated.

**Files:** `backend/app/services/nodes/extract_intent.py` (new)

**System prompt contract:**
- Lists all valid `trigger_type` values
- Lists all valid `integrations` values: `hubspot`, `salesforce`, `sap`, `zendesk`, `jira`, `slack`
- Lists all valid `action_intents` values
- Instructs model to return `"unknown"` for unrecognized trigger types
- Instructs model to set `threshold: null` if no numeric condition is present

**Acceptance criteria:**
- Node function signature: `async def extract_intent_node(state: PlannerState) -> PlannerState`
- On LLM call success: `state["intent"]` is a valid `ExtractedIntent`
- On LLM call failure / parse error: `state["intent"]` is `None` and `state["validation_errors"]` contains the error message
- LLM is sourced via `get_llm()` (not instantiated inline)

**Test:** `tests/test_nodes/test_extract_intent.py`
- Mock `ChatOllama` to return a valid `ExtractedIntent` JSON → assert `state["intent"]` is populated
- Mock `ChatOllama` to raise an exception → assert `state["intent"]` is `None` and errors list is non-empty
- Test does NOT require a running Ollama instance

---

#### TICK-010 — Implement `select_template` node

**What:** Create `backend/app/services/nodes/select_template.py`. Pure business logic — no LLM.

Selection algorithm (in order):
1. If `intent is None` → set `template_id = "large_lead_enrichment"` (safe default)
2. If `trigger_type == "new_lead"` and `threshold is not None` → `large_lead_enrichment`
3. If `trigger_type == "new_lead"` and `threshold is None` → `enterprise_onboarding`
4. If `trigger_type == "deal_closed"` → `deal_closed_processing`
5. If `trigger_type == "account_updated"` → `high_risk_account_alert`
6. If `trigger_type == "support_ticket"` → `churn_risk_response`
7. Default → `large_lead_enrichment`

> **Note on `invoice_created`:** This trigger type is accepted by `ExtractedIntent` (so the LLM can return it without error) but has no dedicated template in this MVP. It falls through to `large_lead_enrichment` via rule 7. The `validation_errors` list should append a warning: `"No template for trigger_type 'invoice_created'; using large_lead_enrichment fallback."` Add a test case asserting this warning is present when `trigger_type == "invoice_created"`.

**Files:** `backend/app/services/nodes/select_template.py` (new)

**Acceptance criteria:**
- Node function signature: `def select_template_node(state: PlannerState) -> PlannerState`
- All 5 template IDs are reachable via the selection algorithm
- `state["template_id"]` is always set (never `None`) after this node

**Test:** `tests/test_nodes/test_select_template.py`
- One test case per template (5 tests) covering each branch
- Test with `intent=None` → asserts `template_id == "large_lead_enrichment"`
- Test unknown trigger type → asserts default is applied

---

#### TICK-011 — Implement template registry

**What:** Create `backend/app/services/templates.py` with the 5 workflow templates from Section 5. Each template is a function `(intent: ExtractedIntent | None) -> list[WorkflowStep]`.

**Files:** `backend/app/services/templates.py` (new)

**Step-ID naming convention:** all step IDs follow `step_{action}` (e.g., `step_get_company`, `step_enrich_company`, `step_create_task`, `step_notify_sales`). This makes condition strings and `depends_on` references predictable without inspecting the returned list.

Per-template step IDs:

| Template | Step IDs (in order) |
|---|---|
| `large_lead_enrichment` | `step_get_company`, `step_enrich_company`, `step_create_task`, `step_notify_sales` |
| `deal_closed_processing` | `step_get_account`, `step_check_compliance`, `step_create_issue`, `step_notify_sales` |
| `high_risk_account_alert` | `step_get_company`, `step_check_compliance`, `step_escalate_ticket`, `step_notify_sales` |
| `churn_risk_response` | `step_get_ticket`, `step_get_contacts`, `step_assign_ticket`, `step_send_dm` |
| `enterprise_onboarding` | `step_get_company`, `step_create_deal`, `step_create_issue`, `step_notify_sales` |

Template rules:
- Steps reference integrations mentioned in `intent.integrations` when a compatible action exists; otherwise use template defaults
- Threshold from `intent.threshold` is compiled into condition strings: `{{steps.STEP_ID.FIELD}} OPERATOR VALUE`
- Default threshold for `large_lead_enrichment` if none detected: `employee_count > 500`
- Step `retry` is set to `RetryConfig(max_attempts=2, delay_ms=500)` on all non-HubSpot steps
- Step `depends_on` is set correctly for the DAG

**Acceptance criteria:**
- Each template function returns a non-empty `list[WorkflowStep]`
- All steps have valid `integration` values from `IntegrationName` enum
- Conditions reference only fields that the preceding step's integration actually returns (see step-ID naming convention in this ticket)
- All `depends_on` references point to step IDs present in the same list

**Test:** `tests/test_templates.py`
- One test per template with a fully populated `ExtractedIntent`
- Assert step count matches expected for each template
- Assert all `depends_on` references resolve to valid step IDs in the returned list
- Assert condition strings compile to the correct format when threshold is provided
- Assert condition strings use defaults when threshold is `None`

---

#### TICK-012 — Implement `fill_parameters` node

**What:** Create `backend/app/services/nodes/fill_parameters.py`. Calls the template registry to produce steps and sets `workflow_name`.

**Files:** `backend/app/services/nodes/fill_parameters.py` (new)

**Acceptance criteria:**
- Node function signature: `def fill_parameters_node(state: PlannerState) -> PlannerState`
- `state["steps"]` is populated from the template function identified by `state["template_id"]`
- `state["workflow_name"]` is set from `intent.workflow_name` if present; otherwise generated as `"{trigger_type.replace('_', ' ').title()} Workflow"`
- Does not call the LLM

**Test:** `tests/test_nodes/test_fill_parameters.py`
- Assert `steps` is non-empty after node runs for each template ID
- Assert `workflow_name` is a non-empty string
- Assert node works when `intent` is `None` (fallback template)

---

#### TICK-013 — Implement `validate_steps` node

**What:** Create `backend/app/services/nodes/validate_steps.py`. Validates the generated step list before returning the plan.

Validation rules:
1. Each `step.integration` must be in `IntegrationName` enum
2. Each `step_id` in `depends_on` must exist in the step list
3. No circular dependencies (topological sort check)
4. All condition strings must be parseable by `SafeConditionEvaluator` (TICK-015)

**Files:** `backend/app/services/nodes/validate_steps.py` (new)

**Acceptance criteria:**
- Node function signature: `def validate_steps_node(state: PlannerState) -> PlannerState`
- Invalid integration → appends to `state["validation_errors"]`
- Invalid `depends_on` reference → appends to `state["validation_errors"]`
- Circular dependency → appends to `state["validation_errors"]`
- Valid steps → `state["validation_errors"]` unchanged

**Test:** `tests/test_nodes/test_validate_steps.py`
- Assert valid step list produces no validation errors
- Assert step with unknown integration produces error
- Assert step with self-referencing `depends_on` produces error
- Assert step with circular `depends_on` (A→B→A) produces error

---

#### TICK-014 — Wire LangGraph graph and replace `RuleBasedPlanner`

**What:** Create `backend/app/services/planner_graph.py` that wires the 4 nodes into a `StateGraph` and exposes a `LangGraphPlanner` class implementing the `WorkflowPlanner` protocol.

```
StateGraph(PlannerState)
  .add_node("extract_intent", extract_intent_node)
  .add_node("select_template", select_template_node)
  .add_node("fill_parameters", fill_parameters_node)
  .add_node("validate_steps", validate_steps_node)
  .add_edge(START, "extract_intent")
  .add_edge("extract_intent", "select_template")
  .add_edge("select_template", "fill_parameters")
  .add_edge("fill_parameters", "validate_steps")
  .add_edge("validate_steps", END)
  .compile()
```

`LangGraphPlanner.plan()` invokes the graph via `await graph.ainvoke(initial_state)`, then constructs `WorkflowPlan` from the returned state. If `validation_errors` is non-empty, raises `ValueError` with the joined error messages.

> **Async/sync note:** `extract_intent_node` is `async def`; all other nodes are `def`. LangGraph handles this correctly when the graph is invoked with `ainvoke` — sync nodes are called directly inside the async event loop without wrapping. Do not use `graph.invoke()` (sync entry point) when any node is async, as it will raise a coroutine error at runtime.

**Files:** `backend/app/services/planner_graph.py` (new), `backend/app/api/routes.py` (swap planner)

**Acceptance criteria:**
- `routes.py` uses `LangGraphPlanner` instead of `RuleBasedPlanner`
- `RuleBasedPlanner` is kept in `planner.py` but unused (do not delete — needed for comparison)
- If Ollama is unreachable, `extract_intent` returns `intent=None` and the graph continues with template defaults; the endpoint does not return 500
- `WorkflowPlan` returned includes `name` field (TICK-004)

**Test:** `tests/test_planner_graph.py`
- Mock `extract_intent_node` to return a fixed `ExtractedIntent` → assert full graph produces a valid `WorkflowPlan`
- Mock `extract_intent_node` to return `intent=None` → assert fallback plan is produced (no error)
- End-to-end: call `LangGraphPlanner.plan()` with mocked LLM → assert `WorkflowPlan` has correct step count for the matched template

---

### EPIC-4: Condition Evaluator

---

#### TICK-015 — Implement `SafeConditionEvaluator`

**What:** Create `backend/app/services/condition_evaluator.py`. Replaces the hardcoded `should_run_step` check in the executor.

**Supported condition format:** `{{steps.STEP_ID.FIELD}} OPERATOR VALUE`

Implementation:
1. Regex-extract `step_id`, `field`, `operator`, `value` from condition string
2. Resolve `step_outputs[step_id][field]` to a Python value
3. Cast `value` to match the resolved value type (int/float/str)
4. Evaluate using `simpleeval` or direct comparison — no `eval()`

Supported operators: `>`, `<`, `>=`, `<=`, `==`, `!=`

Unsupported / unparseable conditions: log a warning, return `True` (fail open, same as current behavior — do not silently break).

**Files:** `backend/app/services/condition_evaluator.py` (new), `backend/app/services/executor.py` (replace `should_run_step`)

**Acceptance criteria:**
- `evaluate(condition, step_outputs)` returns `bool`
- `"{{steps.step_get_company.employee_count}} > 500"` with `employee_count=750` → `True`
- `"{{steps.step_get_company.employee_count}} > 500"` with `employee_count=200` → `False`
- `"{{steps.step_enrich_company.risk_score}} == \"high\""` with `risk_score="high"` → `True`
- `"{{steps.step_enrich_company.risk_score}} == \"high\""` with `risk_score="low"` → `False`
- Missing `step_id` in `step_outputs` → returns `True` (fail open) and logs warning
- Unparseable condition string → returns `True` and logs warning
- No use of `eval()` or `exec()`

**Test:** `tests/test_condition_evaluator.py` — one test per acceptance criterion above (8 tests minimum).

---

### EPIC-5: Executor Enhancements

---

#### TICK-016 — Add step timing to executor

**What:** Wrap each integration call in the executor with `datetime.now(UTC)` before and after. Populate `started_at`, `completed_at`, `duration_ms` on `StepExecutionResult`. Populate `started_at` and `duration_ms` on `WorkflowExecution`.

**Files:** `backend/app/services/executor.py`

**Acceptance criteria:**
- Every `StepExecutionResult` in a completed execution has non-None `started_at`, `completed_at`, `duration_ms`
- Skipped steps have `started_at = completed_at = now()` and `duration_ms = 0`
- `WorkflowExecution.duration_ms` equals sum of all step `duration_ms` values
- All datetimes are timezone-aware UTC

**Test:** `tests/test_executor.py`
- Run a 3-step workflow against mock integrations → assert all step results have timing fields
- Assert `execution.duration_ms >= sum(step.duration_ms for step in results)`
- Assert `started_at < completed_at` for each succeeded step

---

#### TICK-017 — Add step retry logic to executor

**What:** If `step.retry` is set, wrap the integration call in a retry loop. On `IntegrationResult.ok == False`, wait `delay_ms` and retry up to `max_attempts` total. On final failure, record `error` with attempt count. On success within retries, record `output` and note retry count in output metadata.

**Files:** `backend/app/services/executor.py`

**Acceptance criteria:**
- Step with `retry=RetryConfig(max_attempts=3)` that fails twice then succeeds → `StepStatus.succeeded`
- Step with `retry=RetryConfig(max_attempts=2)` that always fails → `StepStatus.failed` after 2 attempts
- Step with `retry=None` that fails → `StepStatus.failed` after 1 attempt (current behavior)
- `duration_ms` includes all retry time

**Test:** `tests/test_executor.py`
- Mock integration to fail N times then succeed → assert final status and attempt count
- Mock integration to always fail with `max_attempts=2` → assert failed after exactly 2 calls

---

#### TICK-039 — Generalize `resolve_template` for arbitrary trigger fields

**What:** The current `resolve_template` in `executor.py` handles only the literal string `"{{trigger.company_id}}"`. New templates (Zendesk churn response, Salesforce deal-closed) need `{{trigger.ticket_id}}`, `{{trigger.account_id}}`, `{{trigger.deal_id}}`, etc. Replace the hardcoded branch with a general parser.

**Files:** `backend/app/services/executor.py`

**New implementation:**
```python
def resolve_template(value, trigger_payload, step_outputs):
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        inner = value[2:-2].strip()
        if inner.startswith("trigger."):
            field = inner.removeprefix("trigger.")
            return trigger_payload.get(field, value)
        if inner.startswith("steps."):
            path = inner.removeprefix("steps.")
            step_id, _, field = path.partition(".")
            return step_outputs.get(step_id, {}).get(field, value)
    return value
```

**Acceptance criteria:**
- `{{trigger.company_id}}` → `trigger_payload["company_id"]` (existing behavior preserved)
- `{{trigger.ticket_id}}` → `trigger_payload["ticket_id"]` (new)
- `{{trigger.account_id}}` → `trigger_payload["account_id"]` (new)
- Unknown `{{trigger.X}}` where X not in payload → returns the raw template string unchanged (fail-open)
- `{{steps.step_get_company.company_id}}` → existing step-output resolution (unchanged)
- Non-template strings returned as-is

**Test:** `tests/test_executor.py` — add 4 tests covering the new trigger field variants and the unknown-field fallback.

---

#### TICK-018 — Add list endpoints to store

**What:** Add `list_workflows(tenant_id, limit, offset)` and `list_executions(tenant_id, limit, offset)` to `InMemoryPrototypeStore`. Return most-recent-first order.

**Files:** `backend/app/services/store.py`

**Acceptance criteria:**
- `list_workflows("tenant_a", limit=10, offset=0)` returns only workflows where `tenant_id == "tenant_a"`
- Results are ordered by insertion order (most recent first)
- `limit` and `offset` work correctly for pagination
- Empty store returns empty list (no exception)

**Test:** `tests/test_store.py`
- Save 5 workflows for tenant A and 2 for tenant B → assert list for A returns 5, list for B returns 2
- Assert `limit=2, offset=0` returns first 2; `limit=2, offset=2` returns next 2

---

### EPIC-6: Integration Expansion

---

#### TICK-019 — Expand `IntegrationName` enum

**What:** Add `salesforce`, `zendesk`, `jira` to `IntegrationName` in `workflow.py`.

**Files:** `backend/app/domain/workflow.py`

**Acceptance criteria:**
- `IntegrationName.salesforce`, `.zendesk`, `.jira` are valid enum members
- Existing serialization/deserialization tests pass unchanged
- Frontend `api.ts` types updated to include new integration names

**Test:** `tests/test_workflow_models.py` — assert all 6 integration names are valid `IntegrationName` values.

---

#### TICK-020 — Expand HubSpot mock (3 new actions)

**What:** Add to `MockHubSpotClient`: `update_company_stage`, `get_contacts`, `create_deal`.

**Files:** `backend/app/integrations/mocks.py`

**New action responses:**
- `update_company_stage` → `{"company_id": ..., "stage": payload.get("stage", "qualified"), "updated": true}`
- `get_contacts` → `{"contacts": [{"id": "ct_001", "name": "Jane Smith", "email": "jane@acme.com"}, {"id": "ct_002", "name": "Bob Lee", "email": "bob@acme.com"}]}`
- `create_deal` → `{"deal_id": "deal_7291", "company_id": ..., "value": payload.get("value", 50000), "stage": "proposal"}`

**Acceptance criteria:**
- All 3 new actions return `IntegrationResult(ok=True, ...)`
- Unknown action still returns `unsupported(...)`
- Existing `get_company` and `create_task` behavior unchanged

**Test:** `tests/test_integrations.py` — one test per new action asserting `ok=True` and expected response keys.

---

#### TICK-021 — Expand SAP mock (2 new actions)

**What:** Add to `MockSAPClient`: `get_credit_rating`, `check_compliance`.

**New action responses:**
- `get_credit_rating` → `{"company_id": ..., "rating": "A", "score": 87, "agency": "SAP Credit"}`
- `check_compliance` → `{"company_id": ..., "status": "approved", "flags": [], "checked_at": "<ISO timestamp>"}`

**Files:** `backend/app/integrations/mocks.py`

**Acceptance criteria:** Same pattern as TICK-020.

**Test:** `tests/test_integrations.py` — one test per action.

---

#### TICK-022 — Expand Slack mock (2 new actions)

**What:** Add to `MockSlackClient`: `send_dm`, `create_channel`.

**New action responses:**
- `send_dm` → `{"user_id": payload.get("user_id"), "message_id": "1718392847.000100", "ok": true}`
- `create_channel` → `{"channel_id": "C08DEMO999", "name": payload.get("name", "workflow-alerts"), "created": true}`

**Files:** `backend/app/integrations/mocks.py`

**Test:** `tests/test_integrations.py` — one test per action.

---

#### TICK-023 — Add Salesforce mock integration

**What:** Create `MockSalesforceClient` with actions: `get_account`, `create_opportunity`, `update_stage`.

**Files:** `backend/app/integrations/mocks.py`, `backend/app/integrations/mocks.py` (`build_mock_registry`)

**Action responses:**
- `get_account` → `{"account_id": ..., "name": "Globex Industries", "annual_revenue": 4200000, "industry": "Technology", "employee_count": 2400}`
- `create_opportunity` → `{"opportunity_id": "OPP-8821", "account_id": ..., "stage": "Proposal", "amount": payload.get("amount", 80000)}`
- `update_stage` → `{"opportunity_id": ..., "stage": payload.get("stage", "Closed Won"), "updated": true}`

**Acceptance criteria:**
- `MockSalesforceClient` registered in `build_mock_registry()`
- `integration = IntegrationName.salesforce`
- All 3 actions return `ok=True`

**Test:** `tests/test_integrations.py` — 3 tests.

---

#### TICK-024 — Add Zendesk mock integration

**What:** Create `MockZendeskClient` with actions: `create_ticket`, `escalate_ticket`, `assign_ticket`.

**Action responses:**
- `create_ticket` → `{"ticket_id": "ZD-9821", "status": "open", "priority": payload.get("priority", "normal"), "subject": payload.get("subject", "Workflow-generated ticket")}`
- `escalate_ticket` → `{"ticket_id": ..., "priority": "urgent", "escalated": true}`
- `assign_ticket` → `{"ticket_id": ..., "assignee_id": payload.get("assignee_id", "agent_01"), "assigned": true}`

**Files:** `backend/app/integrations/mocks.py`

**Test:** `tests/test_integrations.py` — 3 tests.

---

#### TICK-025 — Add Jira mock integration

**What:** Create `MockJiraClient` with actions: `create_issue`, `update_issue`.

**Action responses:**
- `create_issue` → `{"issue_id": "JIRA-4421", "project": payload.get("project", "OPS"), "type": payload.get("type", "Task"), "status": "To Do"}`
- `update_issue` → `{"issue_id": payload.get("issue_id"), "status": payload.get("status", "In Progress"), "updated": true}`

**Files:** `backend/app/integrations/mocks.py`

**Test:** `tests/test_integrations.py` — 2 tests.

---

#### TICK-026 — Realistic varied mock data

**What:** Company data in `MockHubSpotClient.get_company` and `MockSalesforceClient.get_account` varies by `company_id` from a lookup table instead of always returning "Acme Corp 750".

Company profiles (keyed by `company_id`):
| company_id | name | employee_count | industry | annual_revenue |
|---|---|---|---|---|
| `company_demo` | Acme Corp | 750 | Manufacturing | 1_200_000 |
| `company_small` | Initech Ltd | 120 | Consulting | 300_000 |
| `company_large` | Globex Industries | 2400 | Technology | 4_200_000 |
| _(any other)_ | Unknown Co | 50 | Unknown | 0 |

This means the condition `employee_count > 500` evaluates to `True` for `company_demo` and `company_large`, `False` for `company_small` — making the demo visually interesting when you switch `trigger_payload.company_id`.

**Files:** `backend/app/integrations/mocks.py`

**Acceptance criteria:**
- `company_demo` → 750 employees (condition passes)
- `company_small` → 120 employees (condition fails, downstream steps skipped)
- `company_large` → 2400 employees (condition passes)
- Unknown `company_id` → returns 50 employees (condition fails)

**Test:** `tests/test_integrations.py` — 4 tests asserting correct employee count per company_id.

---

### EPIC-7: API Enhancements

---

#### TICK-027 — `GET /workflows` list endpoint

**What:** Add `GET /workflows` to `routes.py` returning paginated list of `WorkflowPlan` for the authenticated tenant.

Query params: `limit: int = 10` (max 100), `offset: int = 0`.

Response: `{"items": [...], "total": N, "limit": 10, "offset": 0}`

**Files:** `backend/app/api/routes.py`, `backend/app/services/store.py`

**Acceptance criteria:**
- Returns only workflows for `auth.tenant_id`
- Respects `limit` and `offset`
- Returns 200 with empty `items` when no workflows exist (not 404)
- Requires valid auth header (401 if missing)

**Test:** `tests/test_routes.py` — save 3 workflows, assert GET /workflows returns 3. Assert cross-tenant request returns 0 items.

---

#### TICK-028 — `GET /executions` list endpoint

**What:** Same pattern as TICK-027 for executions. Returns `WorkflowExecution` items.

**Files:** `backend/app/api/routes.py`, `backend/app/services/store.py`

**Acceptance criteria:** Same pattern as TICK-027.

**Test:** `tests/test_routes.py` — same pattern as TICK-027.

---

### EPIC-8: Frontend Enhancements

---

#### TICK-029 — Example prompt chips

**What:** Add 4 clickable prompt chips below the textarea. Clicking a chip sets the `instruction` state.

Prompts:
1. `"When a new HubSpot lead has more than 500 employees, enrich the company profile, create a follow-up task, and notify the sales team in Slack."`
2. `"When a Salesforce deal closes, check SAP compliance and create a Jira onboarding issue for the ops team."`
3. `"When a high-risk account is updated in HubSpot, escalate a Zendesk support ticket and notify the sales manager via Slack DM."`
4. `"When a support ticket is created in Zendesk, retrieve the HubSpot contacts and assign the ticket to the right team."`

**Files:** `frontend/app/page.tsx`, `frontend/app/styles.css`

**Acceptance criteria:**
- Chips render below the textarea
- Clicking a chip replaces the textarea value with the chip's prompt
- Active chip (matching current instruction) has a distinct visual state
- No API call is triggered on chip click — user still clicks "Plan workflow"

**Test (manual):** Click each chip → verify textarea updates. No network request fired.

---

#### TICK-030 — Workflow name display

**What:** Replace the `plan.workflow_id` UUID in the results header `<h2>` with `plan.name`. Show the workflow ID in a smaller subtext below.

**Files:** `frontend/app/page.tsx`, `frontend/lib/api.ts` (add `name` to `WorkflowPlan` type)

**Acceptance criteria:**
- Results header shows `plan.name` as the primary label (e.g., "Large Lead Enrichment")
- Workflow ID shown as secondary text in monospace, smaller font
- Change is purely presentational — no API changes

**Test (manual):** Run a plan → verify name appears as heading, ID as subtext.

---

#### TICK-031 — Step output panel in execution results

**What:** Expand each execution step `<li>` to show the step's output fields when `status == "succeeded"`. Also show `duration_ms` on each step.

Format per step:
```
✓ Load company from HubSpot    82ms
  name: Acme Corp  |  employee_count: 750  |  industry: Manufacturing
```

For skipped steps: show `⊘ skipped — condition not met` in muted text.

**Files:** `frontend/app/page.tsx`, `frontend/app/styles.css`

**Acceptance criteria:**
- Succeeded step shows key-value pairs from `output` (flat, first level only)
- Skipped step shows skipped label
- Failed step shows `error` message (existing behavior)
- `duration_ms` shown next to step name if present
- No layout breakage on mobile (≤640px)

**Test (manual):** Execute a workflow → verify each step shows correct output. Run with `company_small` company ID → verify downstream steps show as skipped.

---

#### TICK-032 — Execution history panel

**What:** Add a "Recent Runs" section below the main composer panel. On page load, `GET /executions?limit=5` and display the last 5 executions for the tenant.

Each history item shows: execution ID (truncated), workflow ID, status badge, `duration_ms`, `started_at` formatted as relative time ("2 minutes ago").

Refresh history after each new execution.

**Files:** `frontend/app/page.tsx`, `frontend/lib/api.ts` (add `listExecutions()`), `frontend/app/styles.css`

**Acceptance criteria:**
- History loads on mount without blocking the composer
- Each execution links to no detail page (just shows inline data — no navigation)
- Empty state: "No recent runs" message
- History updates immediately after clicking "Execute"
- Errors fetching history are silently ignored (do not block main flow)

**Test (manual):** Execute 3 workflows → verify history shows 3 items in reverse order with correct status badges.

---

### EPIC-9: Tests

---

#### TICK-033 — Tests for `SafeConditionEvaluator` (TICK-015 formalized)

8 unit tests as specified in TICK-015 acceptance criteria. All in `tests/test_condition_evaluator.py`.

---

#### TICK-034 — Tests for template registry

6 tests in `tests/test_templates.py`:
- One test per template (5) asserting step count, integration names, and correct `depends_on` references
- One test asserting threshold is injected into condition string when provided

---

#### TICK-035 — Tests for LangGraph nodes

`tests/test_nodes/` directory with one file per node:
- `test_extract_intent.py` — 2 tests (success + failure with mock LLM)
- `test_select_template.py` — 6 tests (one per branch + default)
- `test_fill_parameters.py` — 3 tests (with intent, without intent, each template)
- `test_validate_steps.py` — 4 tests (valid + 3 invalid cases)

---

#### TICK-036 — Tests for executor enhancements

`tests/test_executor.py` additions:
- 3 timing tests (TICK-016 acceptance criteria)
- 2 retry tests (TICK-017 acceptance criteria)
- Existing prototype flow test still passes unchanged

---

#### TICK-037 — Tests for new integrations

`tests/test_integrations.py`:
- 3 HubSpot action tests (TICK-020)
- 2 SAP action tests (TICK-021)
- 2 Slack action tests (TICK-022)
- 3 Salesforce tests (TICK-023)
- 3 Zendesk tests (TICK-024)
- 2 Jira tests (TICK-025)
- 4 company profile variation tests (TICK-026)

---

#### TICK-038 — Tests for list API endpoints

`tests/test_routes.py` additions:
- 2 tests for `GET /workflows` (TICK-027)
- 2 tests for `GET /executions` (TICK-028)
- 1 test asserting both endpoints require auth

---

## 7. Ticket Dependency Order

```
TICK-001 → TICK-002 → TICK-003          # Infrastructure first
TICK-004 → TICK-005 → TICK-006 → TICK-007  # Domain model (no deps on infra)
TICK-019 (IntegrationName)               # Must precede new mock classes

TICK-008 (State)
  → TICK-009 (extract_intent node)       # Requires TICK-003 (LLM factory)
  → TICK-010 (select_template node)
  → TICK-011 (template registry)         # Requires TICK-019, TICK-006
  → TICK-012 (fill_parameters node)      # Requires TICK-011
  → TICK-013 (validate_steps node)       # Requires TICK-015
  → TICK-014 (wire graph + swap planner) # Requires all nodes + TICK-004

TICK-015 (condition evaluator)           # Independent
  → TICK-016 (timing in executor)        # Requires TICK-005, TICK-007
  → TICK-017 (retry in executor)         # Requires TICK-006
TICK-039 (resolve_template)              # Independent; implement before TICK-011 templates

TICK-020 → TICK-021 → TICK-022 → TICK-023 → TICK-024 → TICK-025  # Any order
  → TICK-026 (varied mock data)

TICK-018 (store list methods)
  → TICK-027 (GET /workflows endpoint)
  → TICK-028 (GET /executions endpoint)

TICK-029 → TICK-030 → TICK-031 → TICK-032  # Frontend (after API endpoints)

TICK-033..TICK-038  # Tests (parallel with implementation of their targets)
```

---

## 8. Definition of Done

A ticket is complete when:
1. Implementation matches all acceptance criteria
2. All tests for that ticket pass (`pytest`)
3. `ruff check` passes with no errors
4. `mypy --strict` passes with no errors on changed files
5. The end-to-end flow (`POST /workflows/plan → POST /workflows/{id}/execute`) still works in Docker

---

## 9. Excluded from This Spec

| Item | Reason |
|---|---|
| Real external API calls | Mocks are expected per README |
| SQLite persistence | In-memory is sufficient for demo; adds setup risk |
| Parallel LangGraph node execution | Out of scope per sequential agent requirement |
| Parallel executor step execution | Deferred — adds complexity, low demo value |
| Auth system beyond demo token | Out of scope for MVP |
| Frontend unit/integration tests | Deferred to post-MVP |
