# API Contract

This is the prototype contract. You may change it if your `SOLUTION.md` explains the trade-off.

## Auth Headers

The starter app uses simple demo headers:

```text
Authorization: Bearer demo-token
X-Tenant-Id: tenant_acme
X-User-Id: user_123
```

In production, this would be replaced with proper identity provider validation and tenant-aware authorization.

## Plan Workflow

```http
POST /workflows/plan
Content-Type: application/json
Authorization: Bearer demo-token
X-Tenant-Id: tenant_acme
X-User-Id: user_123
```

```json
{
  "tenant_id": "tenant_acme",
  "instruction": "When a HubSpot lead has more than 500 employees, enrich it in SAP and notify Slack."
}
```

Expected response:

```json
{
  "workflow_id": "wf_...",
  "tenant_id": "tenant_acme",
  "instruction": "When a HubSpot lead has more than 500 employees, enrich it in SAP and notify Slack.",
  "steps": [
    {
      "step_id": "step_check_lead",
      "name": "Check lead size",
      "integration": "hubspot",
      "action": "get_company",
      "input": {
        "company_id": "{{trigger.company_id}}"
      },
      "depends_on": [],
      "condition": null
    }
  ],
  "assumptions": [],
  "risks": []
}
```

## Execute Workflow

```http
POST /workflows/{workflow_id}/execute
```

Request:

```json
{
  "tenant_id": "tenant_acme",
  "workflow_id": "wf_...",
  "trigger_payload": {
    "company_id": "company_demo"
  }
}
```

Expected response:

```json
{
  "execution_id": "exec_...",
  "workflow_id": "wf_...",
  "tenant_id": "tenant_acme",
  "status": "queued",
  "step_results": []
}
```

## Prototype Caveats

The inherited prototype intentionally uses:

- In-memory storage.
- A keyword-based planner instead of a production LLM abstraction.
- Sequential execution.
- Minimal demo auth.
- Limited validation and error handling.

Your implementation may replace these pieces.

## Inspect Execution

```http
GET /executions/{execution_id}
```

Expected response:

```json
{
  "execution_id": "exec_...",
  "workflow_id": "wf_...",
  "tenant_id": "tenant_acme",
  "status": "succeeded",
  "step_results": [
    {
      "step_id": "step_notify_slack",
      "status": "succeeded",
      "output": {
        "message_id": "msg_123"
      },
      "error": null
    }
  ]
}
```
