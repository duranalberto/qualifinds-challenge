"use client";

import { FormEvent, useState } from "react";

import { executeWorkflow, planWorkflow } from "../lib/api";
import type { WorkflowExecution, WorkflowPlan } from "../lib/api";

const sampleInstruction =
  "When a new HubSpot lead has more than 500 employees, enrich the company profile, create a follow-up task, and notify the sales team in Slack.";

export default function Home() {
  const [instruction, setInstruction] = useState(sampleInstruction);
  const [plan, setPlan] = useState<WorkflowPlan | null>(null);
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await planWorkflow({
        tenantId: "tenant_acme",
        instruction
      });
      setPlan(result);
      setExecution(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  async function onExecute() {
    if (!plan) {
      return;
    }
    setExecuting(true);
    setError(null);

    try {
      const result = await executeWorkflow({
        tenantId: "tenant_acme",
        workflowId: plan.workflow_id
      });
      setExecution(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setExecuting(false);
    }
  }

  return (
    <main className="page">
      <section className="shell">
        <div className="header">
          <div>
            <p className="eyebrow">AI Workflow MVP</p>
            <h1>Workflow Planner</h1>
          </div>
          <span className="status">tenant_acme</span>
        </div>

        <form className="composer" onSubmit={onSubmit}>
          <label htmlFor="instruction">Instruction</label>
          <textarea
            id="instruction"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            rows={6}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Planning..." : "Plan workflow"}
          </button>
        </form>

        {error ? <pre className="error">{error}</pre> : null}

        <section className="results" aria-label="Workflow plan">
          {plan ? (
            <>
              <div className="resultsHeader">
                <h2>{plan.workflow_id}</h2>
                <div className="actions">
                  <span>{plan.steps.length} steps</span>
                  <button type="button" onClick={onExecute} disabled={executing}>
                    {executing ? "Executing..." : "Execute"}
                  </button>
                </div>
              </div>
              <ol className="steps">
                {plan.steps.map((step) => (
                  <li key={step.step_id}>
                    <div>
                      <strong>{step.name}</strong>
                      <p>
                        {step.integration}.{step.action}
                      </p>
                    </div>
                    {step.condition ? <code>{step.condition}</code> : null}
                  </li>
                ))}
              </ol>
              {execution ? (
                <div className="execution">
                  <div className="resultsHeader">
                    <h2>{execution.execution_id}</h2>
                    <span className={`badge ${execution.status}`}>{execution.status}</span>
                  </div>
                  <ol className="steps">
                    {execution.step_results.map((result) => (
                      <li key={result.step_id}>
                        <div>
                          <strong>{result.step_id}</strong>
                          <p>{result.status}</p>
                        </div>
                        {result.error ? <code>{result.error}</code> : null}
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </>
          ) : (
            <p className="empty">Submit an instruction to display the generated workflow.</p>
          )}
        </section>
      </section>
    </main>
  );
}
