# Outbound Sales Crew

A multi-agent outbound sales assistant for marketing agencies. Four role-based
agents (Researcher, Drafter, Reviewer, Sender) are orchestrated by a
hierarchical CrewAI manager. Deterministic guardrails (rate limit, compliance,
opt-out, kill switch) run outside the LLM layer on every send.

## Why CrewAI

Outbound sales is already a role-based team. CrewAI's abstraction maps 1:1 to
how a VP of Sales thinks about their org: Researcher, Copywriter, Compliance
Reviewer, Ops Sender. The hierarchical process gives the manager LLM real
delegation and retry behavior — the same thing a sales manager does with an SDR.

## Setup (local, 3 commands)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill at least one of OPENAI_API_KEY / ANTHROPIC_API_KEY
streamlit run app.py
```

Model IDs are in `.env` — the `DRAFTER_MODEL` defaults to
`claude-sonnet-4-5-20250929`; `claude-sonnet-4-6` is a drop-in replacement.

## Setup (Streamlit Cloud)

1. Deploy the app with `app.py` as the entrypoint and the
   `claude/setup-crewai-sales-33hzJ` branch.
2. Click **Manage app → Settings → Secrets** and paste the contents of
   [`.streamlit/secrets.toml.example`](./.streamlit/secrets.toml.example),
   replacing the `REPLACE_ME` placeholders with real keys.
3. Reboot the app.

The sidebar shows which providers are configured. If you only supply one key,
model routing automatically collapses to that provider so the demo still runs.

You can also paste keys directly into the sidebar for a one-off session — they
live in the process env only and are never written to disk.

## Architecture

| Layer | Location | Purpose |
| --- | --- | --- |
| Crew (agents, tasks, manager) | `crew/` | Role-based LLM workflow |
| Tools | `tools/` | Deterministic `BaseTool` wrappers — never call an LLM |
| Guardrails | `guardrails/` | Pure Python rules (rate, compliance, opt-out, kill) |
| Memory | `memory/` | SQLite event log + per-agency brand voice |
| Evals | `evals/` | Offline golden dataset + online KPI aggregator |
| UI | `app.py` | 6-tab Streamlit demo |

## Model routing (why each pick)

- Researcher → `gpt-4o-mini` — high-volume, low-stakes enrichment.
- Drafter → Claude Sonnet — more human voice, fewer AI-tells.
- Reviewer → Claude Opus — compliance firewall; pay for best judgment.
- Manager → Claude Opus — reasoning-heavy orchestration.
- Sender → `gpt-4o-mini` — mostly deterministic tool-calling.

## Guardrails are NOT agents

Rate limits and legal rules are deterministic. The second an LLM decides
whether GDPR applies, compliance itself becomes probabilistic. The Reviewer
agent uses its LLM for nuanced quality judgment; the guardrail modules in
`guardrails/` handle every binary rule.

## North-star metric

**Rep override rate** — the % of AI drafts a human SDR edits before send.
<15% → AI is helping. >50% → AI is wasting their time. This is a better proxy
for product quality than any LLM-based eval score, because it measures real
user trust with real stakes.

## Demo flow (10 min)

1. **Tab 1 — Live Crew Run**: run a high-quality US lead → approve → send. Then
   run `c_006` (EU, no GDPR basis) → preflight blocks before any LLM call.
2. **Tab 3 — Guardrails**: show rate limit buckets, compliance blocks, opt-out list.
3. **Tab 4 — Online Metrics**: highlight rep override rate.
4. **Tab 6 — Kill Switch**: Spammy Test Co is already auto-paused from seed.

## Running tests

```bash
pytest tests/ -v
```

All guardrail tests pass offline — no API keys required.

## Running the offline eval

```bash
python -m evals.offline_eval
```

Exercises the golden dataset against the deterministic preflight stack.
