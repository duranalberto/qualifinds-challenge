"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  COMPANY_OPTIONS,
  INTEGRATION_CATALOG,
  INTEGRATION_ICONS,
  PROMPT_CHIPS,
  WORKFLOW_CATALOG,
  detectTemplate,
  executeWorkflow,
  listExecutions,
  planWorkflow,
} from "../lib/api";
import type { WorkflowExecution, WorkflowPlan } from "../lib/api";

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export default function Home() {
  const [instruction, setInstruction] = useState(PROMPT_CHIPS[0].prompt);
  const [companyId, setCompanyId] = useState<string>(COMPANY_OPTIONS[0].id);
  const [plan, setPlan] = useState<WorkflowPlan | null>(null);
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [history, setHistory] = useState<WorkflowExecution[]>([]);
  const [showCatalog, setShowCatalog] = useState(false);

  const detected = useMemo(() => detectTemplate(instruction), [instruction]);

  const planIcon = useMemo(
    () =>
      plan
        ? (WORKFLOW_CATALOG.find((w) =>
            plan.name.toLowerCase().includes(w.name.split(" ")[0].toLowerCase())
          )?.icon ?? "⚙️")
        : "⚙️",
    [plan]
  );

  useEffect(() => {
    listExecutions(5)
      .then((data) => setHistory(data.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!showCatalog) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setShowCatalog(false); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [showCatalog]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await planWorkflow({ tenantId: "tenant_acme", instruction });
      setPlan(result);
      setExecution(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  async function onExecute() {
    if (!plan) return;
    setExecuting(true);
    setError(null);
    try {
      const result = await executeWorkflow({ tenantId: "tenant_acme", workflowId: plan.workflow_id, companyId });
      setExecution(result);
      listExecutions(5).then((data) => setHistory(data.items)).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setExecuting(false);
    }
  }

  return (
    <main className="page">
      <section className="shell">

        {/* ── Header ── */}
        <div className="header">
          <div>
            <p className="eyebrow">AI Workflow MVP</p>
            <h1>Workflow Planner</h1>
          </div>
          <span className="status">tenant_acme</span>
        </div>

        {/* ── Composer ── */}
        <form className="composer" onSubmit={onSubmit}>
          <label htmlFor="instruction">Instruction</label>
          <textarea
            id="instruction"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={6}
            maxLength={5000}
            className={detected ? `textarea--${detected.confidence}` : undefined}
          />

          {/* Real-time detection banner */}
          {detected ? (
            <div className={`detectionBanner detectionBanner--${detected.confidence}`}>
              <span className="detectionLabel">✨ Detected</span>
              <span className="detectionWorkflow">{detected.icon} {detected.name}</span>
              <span className="detectionDivider">·</span>
              <span className="detectionIntegrations">
                {detected.integrations.map((i) => (
                  <span key={i} className="detectionIcon" title={i}>
                    {INTEGRATION_ICONS[i]}
                  </span>
                ))}
              </span>
            </div>
          ) : null}

          <div className="chipsRow">
            <div className="chips">
              {PROMPT_CHIPS.map((chip) => (
                <button
                  key={chip.id}
                  type="button"
                  className={`chip${instruction === chip.prompt ? " chip--active" : ""}`}
                  onClick={() => setInstruction(chip.prompt)}
                >
                  {chip.icon} {chip.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              className="browseBtn"
              onClick={() => setShowCatalog(true)}
            >
              Browse all workflows &amp; tools →
            </button>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Planning..." : "Plan workflow"}
          </button>
        </form>

        {error ? <pre className="error">{error}</pre> : null}

        {/* ── Results ── */}
        <section className="results" aria-label="Workflow plan">
          {plan ? (
            <>
              {/* Plan header */}
              <div className="resultsHeader">
                <div>
                  <h2>{planIcon} {plan.name}</h2>
                  <p className="workflowId">{plan.workflow_id}</p>
                </div>
                <div className="actions">
                  <span className="stepCount">{plan.steps.length} steps</span>
                  <select
                    value={companyId}
                    onChange={(e) => setCompanyId(e.target.value)}
                    disabled={executing}
                    className="companySelect"
                  >
                    {COMPANY_OPTIONS.map((opt) => (
                      <option key={opt.id} value={opt.id}>{opt.label}</option>
                    ))}
                  </select>
                  <button type="button" onClick={onExecute} disabled={executing}>
                    {executing ? "Executing…" : "Execute"}
                  </button>
                </div>
              </div>

              {/* Step map */}
              <ol className="steps">
                {plan.steps.map((step, idx) => (
                  <li key={step.step_id} className="stepCard">
                    <div className="stepCardIndex">{idx + 1}</div>
                    <div className="stepCardBody">
                      <div className="stepCardHeader">
                        <span className="stepCardIcon">{INTEGRATION_ICONS[step.integration]}</span>
                        <strong>{step.name}</strong>
                      </div>
                      <p className="stepCardMeta">
                        <span className="stepCardIntegration">{step.integration}</span>
                        <span className="stepCardDot">·</span>
                        {step.action}
                      </p>
                      {step.condition ? <code className="stepCondition">{step.condition}</code> : null}
                    </div>
                  </li>
                ))}
              </ol>

              {/* Execution results */}
              {execution ? (() => {
                const stepMap = Object.fromEntries(plan.steps.map((s) => [s.step_id, s]));
                return (
                  <div className="execution">
                    <div className="resultsHeader">
                      <div>
                        <h2>{execution.execution_id}</h2>
                      </div>
                      <div className="executionMeta">
                        {execution.duration_ms != null && (
                          <span className="executionDuration">⏱ {execution.duration_ms}ms</span>
                        )}
                        <span className={`badge badge--${execution.status}`}>{execution.status}</span>
                      </div>
                    </div>
                    <ol className="steps">
                      {execution.step_results.map((result) => {
                        const planStep = stepMap[result.step_id];
                        const icon = planStep ? INTEGRATION_ICONS[planStep.integration] : "⚙️";
                        const name = planStep?.name ?? result.step_id;
                        return (
                          <li key={result.step_id} className={`stepCard step--${result.status}`}>
                            <div className={`stepCardIndex stepCardIndex--${result.status}`}>
                              {result.status === "succeeded" ? "✓" : result.status === "skipped" ? "⊘" : "✗"}
                            </div>
                            <div className="stepCardBody">
                              <div className="stepCardHeader">
                                <span className="stepCardIcon">{icon}</span>
                                <strong>{name}</strong>
                                {result.duration_ms != null && (
                                  <span className="stepDuration">{result.duration_ms}ms</span>
                                )}
                              </div>
                              {result.status === "skipped" && (
                                <p className="skippedLabel">condition not met — step skipped</p>
                              )}
                              {result.status === "succeeded" && Object.keys(result.output).length > 0 && (
                                <p className="stepOutput">
                                  {Object.entries(result.output)
                                    .filter(([, v]) => typeof v !== "object")
                                    .map(([k, v]) => `${k}: ${String(v)}`)
                                    .join("  ·  ")}
                                </p>
                              )}
                              {result.error && <code>{result.error}</code>}
                            </div>
                          </li>
                        );
                      })}
                    </ol>
                  </div>
                );
              })() : null}
            </>
          ) : (
            <p className="empty">Submit an instruction to see the generated workflow.</p>
          )}
        </section>

        {/* ── History ── */}
        <section className="historyPanel" aria-label="Recent runs">
          <h2 className="historyTitle">Recent Runs</h2>
          {history.length === 0 ? (
            <p className="empty">No recent runs yet.</p>
          ) : (
            <ul className="historyList">
              {history.map((exec) => (
                <li key={exec.execution_id} className="historyItem">
                  <span className={`historyStatus badge--${exec.status}`}>
                    {exec.status === "succeeded" ? "✓" : exec.status === "failed" ? "✗" : "·"}
                  </span>
                  <span className="historyId">{exec.execution_id.slice(0, 20)}</span>
                  <span className={`badge badge--sm badge--${exec.status}`}>{exec.status}</span>
                  {exec.duration_ms != null && (
                    <span className="historyDuration">{exec.duration_ms}ms</span>
                  )}
                  {exec.started_at && (
                    <span className="historyTime">{relativeTime(exec.started_at)}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

      </section>

      {/* ── Catalog modal ── */}
      {showCatalog && (
        <div
          className="catalogOverlay"
          onClick={() => setShowCatalog(false)}
          role="presentation"
        >
          <div
            className="catalogPanel"
            role="dialog"
            aria-modal="true"
            aria-label="Workflows and tools catalog"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="catalogHeader">
              <div>
                <h2 className="catalogTitle">Workflows &amp; Tools</h2>
                <p className="catalogSubtitle">Click a workflow to load it as your instruction</p>
              </div>
              <button
                type="button"
                className="catalogClose"
                onClick={() => setShowCatalog(false)}
                aria-label="Close catalog"
              >
                ✕
              </button>
            </div>

            <div className="catalogBody">
              {/* Workflows */}
              <section className="catalogSection">
                <h3 className="catalogSectionTitle">
                  Workflows <span className="catalogCount">{WORKFLOW_CATALOG.length}</span>
                </h3>
                <div className="catalogGrid">
                  {WORKFLOW_CATALOG.map((wf) => (
                    <button
                      key={wf.id}
                      type="button"
                      className="catalogCard catalogCard--workflow"
                      onClick={() => { setInstruction(wf.prompt); setShowCatalog(false); }}
                    >
                      <span className="catalogCardEmoji">{wf.icon}</span>
                      <strong className="catalogCardName">{wf.name}</strong>
                      <p className="catalogCardTrigger">{wf.trigger}</p>
                      <p className="catalogCardDesc">{wf.description}</p>
                      <div className="catalogCardIntegrations">
                        {wf.integrations.map((i) => (
                          <span key={i} className="catalogCardIntIcon" title={i}>
                            {INTEGRATION_ICONS[i]}
                          </span>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </section>

              {/* Integrations */}
              <section className="catalogSection">
                <h3 className="catalogSectionTitle">
                  Integrations <span className="catalogCount">{INTEGRATION_CATALOG.length}</span>
                </h3>
                <div className="catalogGrid catalogGrid--tools">
                  {INTEGRATION_CATALOG.map((tool) => (
                    <div key={tool.id} className="catalogCard catalogCard--tool">
                      <span className="catalogCardEmoji">{tool.icon}</span>
                      <strong className="catalogCardName">{tool.name}</strong>
                      <p className="catalogCardDesc">{tool.description}</p>
                      <div className="catalogCardActions">
                        {tool.actions.map((a) => (
                          <span key={a} className="actionTag">{a}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
