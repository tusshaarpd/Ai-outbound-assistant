# Outbound Sales Crew

A multi-agent outbound sales assistant for marketing agencies. Four role-based
agents (Researcher, Drafter, Reviewer, Sender) are orchestrated by a
hierarchical CrewAI manager. Deterministic guardrails (rate limit, compliance,
opt-out, kill switch) run outside the LLM layer on every send.

> **The point in one line:** the AI is the easy part. The hard part is the
> guardrails that keep one bad agency from destroying sender reputation for
> the other 500.

## Why CrewAI

Outbound sales is already a role-based team. CrewAI's abstraction maps 1:1 to
how a VP of Sales thinks about their org: Researcher, Copywriter, Compliance
Reviewer, Ops Sender. The hierarchical process gives the manager LLM real
delegation and retry behavior — the same thing a sales manager does with an SDR.

## Setup (local, 3 commands)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill OPENAI_API_KEY
streamlit run app.py
```

This deploy is **OpenAI-only** — every agent routes to a `gpt-*` model.
`OPENAI_API_KEY` is the only provider key required.

## Setup (Streamlit Cloud)

1. Deploy the app with `app.py` as the entrypoint and the
   `claude/setup-crewai-sales-33hzJ` branch.
2. Click **Manage app → Settings → Secrets** and paste:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
3. Reboot the app.

You can also paste a key directly into the sidebar for a one-off session — it
lives in the process env only and is never written to disk.

---

## What you'll see in the UI

The app has **6 tabs**, each answering one question a PM gets in an interview.
Below is what each tab does, what to click, and how to read the result.

### Tab 1 — 🎯 Live Crew Run

**What it does.** Runs ONE prospect through the entire 4-agent pipeline end-to-end.

**Inputs.** Pick a prospect, pick an agency, pick a channel (`email` / `sms`),
hit **Run Crew**.

**What happens, step by step.**
1. **Pre-flight guardrails** run first — pure Python, no LLM calls. If the
   contact is opted-out, recently contacted, or in a paused agency, the run
   stops here. *This saves API spend on hopeless contacts.*
2. If preflight passes, the **Crew kicks off**. The Manager LLM delegates to
   the Researcher → Drafter → Reviewer → Sender in order.
3. The final JSON output is rendered inline.

**How to read the result.**

| Field | What it means |
| --- | --- |
| `status: "blocked"` + `blocked_at` | A guardrail caught it before any LLM ran. The `reason` tells you which one (e.g. `missing_gdpr_legal_basis`, `contact_opted_out`, `per_contact_daily_cap`). |
| `status: "completed"` | The Crew ran end-to-end. Look at `crew_output` for the message draft + reviewer decision. |
| `human_review_required: true` | Agency hasn't sent enough messages to earn autonomous send rights yet — the SDR must approve before dispatch. |

**Try these contacts to see every path:**
- `c_001` (Maya Patel) — happy path, full crew runs.
- `c_006` (Anna Becker, EU) — preflight blocks with `missing_gdpr_legal_basis`.
- `c_009` (Thomas Reed) — preflight blocks with `contact_opted_out`.
- `c_011` (Marcus Hill) — preflight blocks with `per_contact_daily_cap`.
- `c_012` (Emma Torres, student) — Researcher should flag low confidence.
- Any contact with the **Spammy Test Co** agency — kill switch blocks at `kill_switch` stage.

### Tab 2 — 📥 Campaign Builder

**What it does.** Batch preflight over a slice of your CRM. Lets an agency
owner see "of these 50 prospects, how many will the system actually send to,
and why is it blocking the rest?" — without any engineer involvement.

**How to read the result.** A table with one row per prospect:
- `ok = True` → would send if you ran the crew.
- `ok = False` + `stage` + `reason` → preflight blocked it; reason tells you which guardrail.

The summary at the bottom (e.g. *"32/50 pass preflight"*) is the deliverability
budget for the campaign.

### Tab 3 — 🛡 Guardrails Dashboard

**What it does.** Live status of every deterministic guardrail per agency.

**Three sections:**

1. **Agency status table.** Status (`active` / `paused`), total messages sent,
   pause reason if any.
2. **Rate limit buckets.** For a chosen contact + agency, shows how full each
   bucket is:
   - `per_contact_24h` (cap 1) — has this contact been emailed today?
   - `per_contact_30d` (cap 5) — sequence cap.
   - `per_agency_24h` (cap 100 default, 2000 once established).
3. **Recent guardrail blocks.** A log of every block in the last 50 events
   with timestamp, guardrail name, and reason. *This is the audit trail.*

**The PM message:** *"The guardrails ARE the product. The AI is the commodity."*

### Tab 4 — 📊 Online Metrics

**What it does.** Live business KPIs from the event log.

**Six metrics shown** (with target thresholds in tooltips):

| Metric | Target | Reads |
| --- | --- | --- |
| Sent (30d) | – | Volume — context for everything else |
| Response rate | ≥8% | Does the message land? |
| Meeting booked rate | ≥1.5% | Does it convert? |
| Unsubscribe rate | <1% | Are we annoying people? |
| Spam complaint rate | <0.08% | Are we destroying deliverability? |
| **★ Rep override rate** | **<15%** | **North-star: how often human SDRs edit drafts before send.** |

**Why "rep override rate" is the north-star.** It measures real user trust with
real stakes. <15% means the AI is helping. >50% means the SDR is rewriting
everything — we're in their way. It's a better proxy for product quality than
any LLM-based eval score.

> Fresh deploy will show 0% across the board until you run a few crews. Run
> some on Tab 1 to populate history.

### Tab 5 — 🧪 Offline Evals

**What it does.** Runs the golden-dataset (`evals/golden_dataset.json`)
through the deterministic preflight stack and reports pass/fail per case.

**Click "Run eval"** → table of 10 cases.

**How to read it.**
- `passed = True` for every row → preflight is correctly blocking the cases
  it should block and passing the cases it should pass.
- `passed = False` → regression. The bottom of the tab shows total
  pass/fail. Treat this as a deploy gate.

### Tab 6 — 🚨 Kill Switch & Admin

**What it does.** The "what to push when something is on fire at 2am" panel.

**Per agency you can:**
- See live spam-complaint, unsubscribe, and bounce rates.
- **Pause** an agency manually (e.g. customer reports they're getting spam
  reports).
- **Resume** a paused agency.
- **Re-evaluate health** — runs the kill-switch logic on demand and shows
  which thresholds (if any) tripped.

**Spammy Test Co** is shipped pre-paused so you can show the auto-pause
state without having to trigger it.

The bottom shows the **30 most recent events** across all agencies — useful
for spot-checking what just happened.

---

## Architecture at a glance

| Layer | Location | Purpose |
| --- | --- | --- |
| Crew (agents, tasks, manager) | `crew/` | Role-based LLM workflow |
| Tools | `tools/` | Deterministic `BaseTool` wrappers — never call an LLM |
| Guardrails | `guardrails/` | Pure Python rules (rate, compliance, opt-out, kill) |
| Memory | `memory/` | SQLite event log + per-agency brand voice |
| Evals | `evals/` | Offline golden dataset + online KPI aggregator |
| UI | `app.py` | 6-tab Streamlit demo |

## Model routing (OpenAI-only)

- Researcher → `gpt-4o-mini` — high-volume, low-stakes enrichment.
- Drafter → `gpt-4o` — quality writing.
- Reviewer → `gpt-4o` — compliance firewall; pay for best judgment.
- Manager → `gpt-4o` — reasoning-heavy orchestration.
- Sender → `gpt-4o-mini` — mostly deterministic tool-calling.

The original spec routes Drafter/Reviewer/Manager through Anthropic
(Sonnet/Opus). That dual-provider routing is preserved in `git log` — the
deployed app collapses to a single provider for simplicity. To switch to
Anthropic, restore the Anthropic LLM instances in `crew/agents.py` and add
`ANTHROPIC_API_KEY` to your environment.

## Guardrails are NOT agents

Rate limits and legal rules are deterministic. The second an LLM decides
whether GDPR applies, compliance itself becomes probabilistic. The Reviewer
agent uses its LLM for nuanced quality judgment; the guardrail modules in
`guardrails/` handle every binary rule.

## Demo flow (10 min)

1. **Tab 1 — Live Crew Run**: run `c_001` → approve → send. Then run `c_006`
   (EU, no GDPR basis) → preflight blocks before any LLM call. *Talking
   point: "guardrails save API spend on hopeless contacts."*
2. **Tab 3 — Guardrails Dashboard**: rate limit buckets, compliance block log,
   opt-out list. *"The guardrails ARE the product."*
3. **Tab 4 — Online Metrics**: highlight rep override rate. *"This is the
   single number I care about."*
4. **Tab 6 — Kill Switch**: Spammy Test Co is already auto-paused.
   *"At 2am someone needs a single button."*

## Running tests

```bash
pytest tests/ -v
```

All 21 guardrail tests pass offline — no API keys required.

## Running the offline eval

```bash
python -m evals.offline_eval
```

Exercises the 10-case golden dataset against the deterministic preflight stack.
Returns non-zero exit code if any case fails — wire into CI as a deploy gate.
