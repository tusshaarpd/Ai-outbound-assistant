# CLAUDE.md — Outbound Sales Crew

## What this is
A multi-agent outbound sales assistant for marketing agencies, built on CrewAI.
Four LLM agents (Researcher, Drafter, Reviewer, Sender) are orchestrated by a
hierarchical manager. Deterministic guardrails (rate limit, compliance,
opt-out, kill switch) sit outside the LLM layer and run on every send.

## Architecture at a glance
- `crew/` — Agent + Task + Crew definitions. Hierarchical process, manager LLM.
- `tools/` — `BaseTool` subclasses the agents call. All deterministic wrappers.
- `guardrails/` — Pure Python. NOT agents. Compliance must not be probabilistic.
- `memory/` — SQLite (`contact_history`, `agency_state`) + brand voice loader.
- `evals/` — Offline golden-dataset runner + online KPI aggregator.
- `data/` — Seed JSON (50 contacts, 3 agencies) + generated `outbound.db`.
- `app.py` — 6-tab Streamlit demo UI.

## Model routing (why each pick)
- Researcher → `gpt-4o-mini`: high-volume, low-stakes enrichment.
- Drafter → Claude Sonnet: human-sounding copy, fewer AI-tells.
- Reviewer → Claude Opus: compliance firewall, highest-judgment model.
- Manager → Claude Opus: orchestrates delegation and retries.
- Sender → `gpt-4o-mini`: mostly deterministic tool-calling, no creativity.

## Guardrails are not agents
Rate limits and legal rules are deterministic Python. An LLM never decides
whether CAN-SPAM applies. The Reviewer agent uses its LLM for nuanced quality
judgment; the guardrail modules handle binary rules.

## North-star metric
Rep override rate: % of drafts a human SDR edits before send.
- <15% → AI is helping.
- >50% → AI is wasting their time.

## How to run
```
pip install -r requirements.txt
cp .env.example .env        # fill in OPENAI_API_KEY + ANTHROPIC_API_KEY
streamlit run app.py
```
