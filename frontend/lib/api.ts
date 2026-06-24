const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";

export type IntegrationName =
  | "hubspot" | "sap" | "slack" | "salesforce"
  | "zendesk" | "jira" | "stripe" | "gmail";

export type WorkflowStep = {
  step_id: string;
  name: string;
  integration: IntegrationName;
  action: string;
  input: Record<string, unknown>;
  depends_on: string[];
  condition: string | null;
};

export type WorkflowPlan = {
  workflow_id: string;
  tenant_id: string;
  instruction: string;
  name: string;
  steps: WorkflowStep[];
  assumptions: string[];
  risks: string[];
};

export type StepExecutionResult = {
  step_id: string;
  status: "pending" | "running" | "succeeded" | "failed" | "skipped";
  output: Record<string, unknown>;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
};

export type WorkflowExecution = {
  execution_id: string;
  workflow_id: string;
  tenant_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  step_results: StepExecutionResult[];
  started_at: string | null;
  duration_ms: number | null;
};

export type PaginatedExecutions = {
  items: WorkflowExecution[];
  total: number;
  limit: number;
  offset: number;
};

// ── Integration icons ─────────────────────────────────────────────────────────

export const INTEGRATION_ICONS: Record<IntegrationName, string> = {
  hubspot:    "🟠",
  sap:        "🔷",
  slack:      "💬",
  salesforce: "☁️",
  zendesk:    "🎫",
  jira:       "🔵",
  stripe:     "💳",
  gmail:      "📧",
};

// ── Integration catalog ───────────────────────────────────────────────────────

export type IntegrationEntry = {
  id: IntegrationName;
  icon: string;
  name: string;
  description: string;
  actions: string[];
};

export const INTEGRATION_CATALOG: IntegrationEntry[] = [
  {
    id: "hubspot",
    icon: "🟠",
    name: "HubSpot",
    description: "CRM for contacts, companies, deals, and sales tasks.",
    actions: ["get_company", "create_task", "create_deal", "get_contacts", "update_company_stage"],
  },
  {
    id: "salesforce",
    icon: "☁️",
    name: "Salesforce",
    description: "Enterprise CRM for accounts, opportunities, and pipeline.",
    actions: ["get_account", "create_opportunity", "update_stage"],
  },
  {
    id: "sap",
    icon: "🔷",
    name: "SAP",
    description: "ERP system for compliance checks, credit ratings, and enrichment.",
    actions: ["enrich_company", "get_credit_rating", "check_compliance"],
  },
  {
    id: "slack",
    icon: "💬",
    name: "Slack",
    description: "Team messaging for channel alerts, DMs, and workspace management.",
    actions: ["send_message", "send_dm", "create_channel"],
  },
  {
    id: "zendesk",
    icon: "🎫",
    name: "Zendesk",
    description: "Customer support platform for tickets, escalations, and assignment.",
    actions: ["create_ticket", "escalate_ticket", "assign_ticket"],
  },
  {
    id: "jira",
    icon: "🔵",
    name: "Jira",
    description: "Project tracking for issues, tasks, and engineering sprints.",
    actions: ["create_issue", "update_issue"],
  },
  {
    id: "stripe",
    icon: "💳",
    name: "Stripe",
    description: "Payment processing for invoices, charges, and subscriptions.",
    actions: ["create_invoice", "finalize_invoice", "charge_customer"],
  },
  {
    id: "gmail",
    icon: "📧",
    name: "Gmail",
    description: "Email for outbound communications, drafts, and thread tracking.",
    actions: ["send_email", "create_draft", "get_thread"],
  },
];

// ── Workflow catalog ──────────────────────────────────────────────────────────

export type WorkflowEntry = {
  id: string;
  icon: string;
  name: string;
  trigger: string;
  description: string;
  integrations: IntegrationName[];
  prompt: string;
};

export const WORKFLOW_CATALOG: WorkflowEntry[] = [
  {
    id: "large_lead_enrichment",
    icon: "📊",
    name: "Large Lead Enrichment",
    trigger: "new_lead + threshold",
    description: "Triggers on leads with 500+ employees. Enriches the company via SAP, creates a HubSpot follow-up task, and alerts the sales team.",
    integrations: ["hubspot", "sap", "slack"],
    prompt: "When a new HubSpot lead has more than 500 employees, enrich the company profile, create a follow-up task, and notify the sales team in Slack.",
  },
  {
    id: "enterprise_onboarding",
    icon: "🚀",
    name: "Enterprise Onboarding",
    trigger: "new_lead",
    description: "Triggers on any new lead. Creates a HubSpot deal, opens a Jira onboarding issue for ops, and notifies the sales channel.",
    integrations: ["hubspot", "jira", "slack"],
    prompt: "When a new enterprise lead arrives without a size threshold, create a HubSpot deal, open a Jira onboarding issue for the ops team, and notify the sales team in Slack.",
  },
  {
    id: "deal_closed_processing",
    icon: "💰",
    name: "Deal Closed Processing",
    trigger: "deal_closed",
    description: "Triggers when a Salesforce deal closes. Runs a SAP compliance check, creates a Jira handoff issue, and notifies the sales channel.",
    integrations: ["salesforce", "sap", "jira", "slack"],
    prompt: "When a Salesforce deal closes, check SAP compliance, create a Jira handoff issue for the ops team, and notify the sales channel in Slack.",
  },
  {
    id: "high_risk_account_alert",
    icon: "⚠️",
    name: "High Risk Account Alert",
    trigger: "account_updated",
    description: "Triggers when an account is updated. Checks SAP risk compliance, escalates a Zendesk ticket, and sends a Slack DM to the sales manager.",
    integrations: ["hubspot", "sap", "zendesk", "slack"],
    prompt: "When a high-risk account is updated in HubSpot, check SAP compliance, escalate the Zendesk support ticket, and notify the sales manager via Slack DM.",
  },
  {
    id: "churn_risk_response",
    icon: "🔄",
    name: "Churn Risk Response",
    trigger: "support_ticket",
    description: "Triggers on a new Zendesk support ticket. Retrieves HubSpot contacts and assigns the ticket to the right agent automatically.",
    integrations: ["zendesk", "hubspot", "slack"],
    prompt: "When a support ticket is created in Zendesk, retrieve the HubSpot contacts and assign the ticket to the right team.",
  },
  {
    id: "invoice_payment_processing",
    icon: "🧾",
    name: "Invoice Payment Processing",
    trigger: "invoice_created",
    description: "Triggers when a new invoice is created. Creates and charges the customer via Stripe, then notifies the finance channel in Slack.",
    integrations: ["hubspot", "stripe", "slack"],
    prompt: "When a new invoice is created, charge the customer via Stripe and notify the finance team in Slack.",
  },
  {
    id: "contract_renewal_automation",
    icon: "📋",
    name: "Contract Renewal",
    trigger: "contract_expiring",
    description: "Triggers when a contract is about to expire. Pulls account data, fetches contacts from HubSpot, and sends a renewal email via Gmail.",
    integrations: ["salesforce", "hubspot", "gmail", "slack"],
    prompt: "When a contract is expiring next month, send a renewal email via Gmail and alert the sales team in Slack.",
  },
];

// ── Prompt chips (structured, one per workflow) ───────────────────────────────

export type PromptChip = {
  id: string;
  icon: string;
  label: string;
  prompt: string;
};

export const PROMPT_CHIPS: PromptChip[] = WORKFLOW_CATALOG.map((wf) => ({
  id: wf.id,
  icon: wf.icon,
  label: wf.name.split(" ").slice(0, 2).join(" "),
  prompt: wf.prompt,
}));

// ── Real-time template detection ──────────────────────────────────────────────

export type TemplateMatch = {
  id: string;
  name: string;
  icon: string;
  confidence: "high" | "medium";
  integrations: IntegrationName[];
};

const _SIGNALS = WORKFLOW_CATALOG.map((wf) => ({
  id: wf.id,
  integrations: wf.integrations,
  keywords: wf.prompt.toLowerCase().split(/\W+/).filter((w) => w.length > 3),
}));

// Supplement with domain keywords that the prompt wording might miss
const _KEYWORD_OVERRIDES: Record<string, string[]> = {
  large_lead_enrichment:       ["employee", "employees", "500", "enrich", "hubspot"],
  enterprise_onboarding:       ["onboard", "onboarding", "enterprise", "welcome"],
  deal_closed_processing:      ["deal", "close", "closed", "won", "signed", "signing"],
  high_risk_account_alert:     ["risk", "high-risk", "alert", "escalate", "account"],
  churn_risk_response:         ["churn", "support", "ticket", "zendesk", "cancel", "assign"],
  invoice_payment_processing:  ["invoice", "payment", "billing", "charge", "stripe", "bill", "pay"],
  contract_renewal_automation: ["contract", "renewal", "renew", "expir", "expire", "expires", "expiring"],
};

export function detectTemplate(instruction: string): TemplateMatch | null {
  if (instruction.trim().length < 10) return null;
  const lower = instruction.toLowerCase();
  let best: (typeof _SIGNALS)[0] | null = null;
  let bestScore = 0;
  for (const t of _SIGNALS) {
    const allKeywords = [...t.keywords, ...(_KEYWORD_OVERRIDES[t.id] ?? [])];
    const score = [...new Set(allKeywords)].filter((k) => lower.includes(k)).length;
    if (score > bestScore) { bestScore = score; best = t; }
  }
  if (!best || bestScore === 0) return null;
  const wf = WORKFLOW_CATALOG.find((w) => w.id === best!.id)!;
  return {
    id: best.id,
    name: wf.name,
    icon: wf.icon,
    confidence: bestScore >= 2 ? "high" : "medium",
    integrations: best.integrations,
  };
}

// ── Company selector ──────────────────────────────────────────────────────────

export const COMPANY_OPTIONS = [
  { id: "company_demo",  label: "Acme Corp (750 emp — threshold passes)" },
  { id: "company_small", label: "Initech Ltd (120 emp — threshold fails)" },
  { id: "company_large", label: "Globex Industries (2400 emp — passes)" },
] as const;

// ── API calls ─────────────────────────────────────────────────────────────────

const AUTH_HEADERS = {
  "Content-Type": "application/json",
  Authorization: "Bearer demo-token",
  "X-Tenant-Id": "tenant_acme",
  "X-User-Id": "frontend_user",
};

export async function planWorkflow({
  tenantId,
  instruction,
}: {
  tenantId: string;
  instruction: string;
}): Promise<WorkflowPlan> {
  const response = await fetch(`${API_BASE_URL}/workflows/plan`, {
    method: "POST",
    headers: AUTH_HEADERS,
    body: JSON.stringify({ tenant_id: tenantId, instruction }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<WorkflowPlan>;
}

export async function executeWorkflow({
  tenantId,
  workflowId,
  companyId = "company_demo",
}: {
  tenantId: string;
  workflowId: string;
  companyId?: string;
}): Promise<WorkflowExecution> {
  const response = await fetch(`${API_BASE_URL}/workflows/${workflowId}/execute`, {
    method: "POST",
    headers: AUTH_HEADERS,
    body: JSON.stringify({
      tenant_id: tenantId,
      workflow_id: workflowId,
      trigger_payload: { company_id: companyId },
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<WorkflowExecution>;
}

export async function listExecutions(limit = 5): Promise<PaginatedExecutions> {
  const response = await fetch(`${API_BASE_URL}/executions?limit=${limit}`, {
    headers: AUTH_HEADERS,
  });
  if (!response.ok) throw new Error(`Failed to fetch executions: ${response.status}`);
  return response.json() as Promise<PaginatedExecutions>;
}
