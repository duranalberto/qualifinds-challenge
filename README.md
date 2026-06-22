# Prototype To Production MVP: AI Workflow Challenge

This repository contains a rough prototype for an AI workflow product. It demonstrates the basic idea, but it is not ready to be used by real customers.

Your task is to review the prototype and improve it into a stronger MVP.

We are intentionally not prescribing exactly what to change. Part of the assessment is how you identify the most important gaps, decide what to improve within the timebox, and explain the trade-offs behind your choices.

## Product Scenario

The product receives a natural-language automation request and turns it into executable workflow steps.

Example:

```text
When a new HubSpot lead has more than 500 employees, enrich the company profile, create a follow-up task, and notify the sales team in Slack.
```

The current prototype includes a basic backend, mocked integrations, and a minimal frontend.

## Timebox

Spend 3 to 4 hours.

This is intentionally a short exercise. Do not try to build a complete production platform. Focus on the changes that most improve the prototype's ability to work as a credible MVP.

A smaller, coherent solution that you deeply understand is better than a broad rewrite.

## Your Task

Improve the prototype so that it is closer to something that could be used by real users.

You may change the architecture, API, data model, frontend, tests, or developer experience as you see fit.

You should be prepared to explain:

- What you changed.
- Why you chose those changes.
- What risks remain.
- What you would do next if you had more time.

## Expectations

Your solution should preserve a usable end-to-end product flow:

- A user can submit a natural-language instruction.
- The system can produce a workflow.
- The workflow can be executed against mocked integrations.
- The user can inspect the result.

Beyond that, use your judgment.

We care most about backend quality, product judgment, workflow orchestration, reliability, and your ability to reason about the path from prototype to production-ready MVP.

The frontend only needs to support the core workflow clearly.

## AI And Tooling

Use whatever development tools you normally use.

You are responsible for understanding and defending everything you submit. During the interview, we will review your decisions, code, and trade-offs in detail.

## Running The Project

### Docker

The quickest path is Docker Compose:

```bash
docker compose up --build
```

Then open:

```text
Frontend: http://localhost:3100
Backend:  http://localhost:8100
Health:   http://localhost:8100/health
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

Run tests:

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

By default, the frontend expects the backend at `http://localhost:8100`.

## Deliverables

Submit:

- Source code.
- Tests where you believe they add the most value.
- A short `SOLUTION.md` explaining:
  - What you changed.
  - Why you prioritized those changes.
  - How to run the project.
  - What you would improve next.

## Notes

- Do not use real credentials or customer data.
- Mocked external integrations are expected.
- Keep the project easy to run locally.
