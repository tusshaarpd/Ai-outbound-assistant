"""Streamlit demo: 6 tabs from spec Part 9."""
import json
import time
from datetime import datetime

import pandas as pd
import streamlit as st

import config  # imports secrets_loader → promotes st.secrets into env
from evals import offline_eval, online_metrics
from guardrails import kill_switch
from guardrails.rate_limiter import bucket_status
from memory.brand_voice import list_agencies, pause_agency, resume_agency
from memory.contact_history import list_contacts, list_recent_events
from memory.db import connect, init_db

st.set_page_config(page_title="Outbound Sales Crew", layout="wide")
init_db()

# --- Sidebar: OpenAI API key status + quick-add for the current session ---
with st.sidebar:
    st.subheader("OpenAI API key")
    has_openai = config.HAS_OPENAI
    if has_openai:
        st.success("OpenAI key configured")
    else:
        st.warning(
            "No OpenAI key detected. Paste one below for this session, "
            "or set `OPENAI_API_KEY` under Streamlit `Manage app → Secrets`."
        )

    with st.expander("Add / override key for this session", expanded=not has_openai):
        st.caption(
            "Stored in process env only — never written to disk. "
            "For persistent keys on Streamlit Cloud, use "
            "`Manage app → Secrets` with variable name `OPENAI_API_KEY`."
        )
        openai_in = st.text_input(
            "OPENAI_API_KEY",
            value="",
            type="password",
            placeholder="sk-...",
            help="Powers all 4 agents in OpenAI-only mode.",
        )
        if st.button("Apply key", use_container_width=True):
            import os
            if openai_in:
                os.environ["OPENAI_API_KEY"] = openai_in
                # Re-alias so CrewAI's ChromaDB memory picks it up.
                os.environ["CHROMA_OPENAI_API_KEY"] = openai_in
                st.success("Applied. Reload the page to recompute model routing.")
                st.rerun()
            else:
                st.error("Paste a key first.")

TAB_NAMES = [
    "Live Crew Run",
    "Campaign Builder",
    "Guardrails Dashboard",
    "Online Metrics",
    "Offline Evals",
    "Kill Switch & Admin",
]
tabs = st.tabs(TAB_NAMES)

# ===========================================================================
# TAB 1: LIVE CREW RUN
# ===========================================================================
with tabs[0]:
    st.header("Live Crew Run")
    st.caption(
        "One contact end-to-end. See Researcher → Drafter → Reviewer → Sender in order. "
        "Guardrails run before the crew — no API calls wasted on blocked contacts."
    )

    contacts = list_contacts()
    agencies = list_agencies()
    col_a, col_b, col_c, col_d = st.columns([2, 2, 1, 1])
    with col_a:
        contact_choice = st.selectbox(
            "Prospect",
            contacts,
            format_func=lambda c: f"{c['contact_id']} — {c['name']} ({c.get('quality_note','standard')})",
        )
    with col_b:
        agency_choice = st.selectbox(
            "Agency",
            agencies,
            format_func=lambda a: f"{a['agency_id']} — {a['name']} [{a['status']}]",
        )
    with col_c:
        channel = st.selectbox("Channel", ["email", "sms"], index=0)
    with col_d:
        st.write("")
        run_btn = st.button("Run Crew", type="primary", use_container_width=True)

    if run_btn:
        # Import here so the app loads even without API keys.
        from guardrails.preflight import preflight_guardrails

        pre = preflight_guardrails(
            contact_choice["contact_id"], agency_choice["agency_id"], channel
        )
        st.subheader("Pre-flight guardrails")
        if pre["ok"]:
            st.success(
                f"All guardrails passed. Human review required: "
                f"{pre.get('human_review_required')}"
            )
        else:
            st.error(
                f"BLOCKED at `{pre['stage']}` — reason: `{pre['reason']}`. "
                "Crew not invoked (saves LLM cost)."
            )

        if pre["ok"]:
            st.subheader("Crew execution")
            with st.spinner("Manager delegating to Researcher → Drafter → Reviewer → Sender…"):
                t0 = time.time()
                try:
                    from crew.crew_builder import run_outbound
                    out = run_outbound(
                        contact_choice["contact_id"], agency_choice["agency_id"], channel
                    )
                    elapsed = time.time() - t0
                    st.success(f"Completed in {elapsed:.1f}s")
                    st.json(out)
                except Exception as e:
                    st.error(f"Crew run failed: {e}")
                    st.caption(
                        "If this is an API-key error, fill .env with OPENAI_API_KEY "
                        "and ANTHROPIC_API_KEY."
                    )

# ===========================================================================
# TAB 2: CAMPAIGN BUILDER
# ===========================================================================
with tabs[1]:
    st.header("Campaign Builder")
    st.caption(
        "Batch run over a slice of your CRM. Preview first, then launch. "
        "An agency owner should be able to run this without an engineer."
    )

    agencies = list_agencies()
    agency_choice = st.selectbox(
        "Agency",
        agencies,
        key="campaign_agency",
        format_func=lambda a: f"{a['agency_id']} — {a['name']}",
    )
    channel = st.selectbox("Channel", ["email", "sms"], key="campaign_channel")
    contacts = list_contacts()
    n = st.slider("Prospects to include", 1, len(contacts), 5)

    st.subheader("Preview — first 3 prospects")
    preview_df = pd.DataFrame(contacts[: min(3, n)])[
        ["contact_id", "name", "company", "title", "region", "quality_note"]
    ]
    st.dataframe(preview_df, use_container_width=True)

    if st.button("Preflight all", key="campaign_preflight"):
        from guardrails.preflight import preflight_guardrails
        rows = []
        for c in contacts[:n]:
            pre = preflight_guardrails(
                c["contact_id"], agency_choice["agency_id"], channel
            )
            rows.append(
                {
                    "contact_id": c["contact_id"],
                    "name": c["name"],
                    "ok": pre["ok"],
                    "stage": pre["stage"],
                    "reason": pre["reason"],
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        st.caption(
            f"{df['ok'].sum()}/{len(df)} pass preflight. The rest are blocked "
            "deterministically without hitting an LLM."
        )

# ===========================================================================
# TAB 3: GUARDRAILS DASHBOARD
# ===========================================================================
with tabs[2]:
    st.header("Guardrails Dashboard")
    st.caption("The guardrails ARE the product. The AI is the commodity.")

    agencies = list_agencies()

    st.subheader("Agency status")
    rows = []
    for a in agencies:
        rows.append(
            {
                "agency_id": a["agency_id"],
                "name": a["name"],
                "status": a["status"],
                "messages_sent_total": a["messages_sent_total"],
                "pause_reason": a.get("pause_reason"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("Rate limit buckets (per selected contact + agency)")
    col1, col2 = st.columns(2)
    with col1:
        cmp_contact = st.selectbox(
            "Contact",
            list_contacts(),
            key="bucket_contact",
            format_func=lambda c: c["contact_id"],
        )
    with col2:
        cmp_agency = st.selectbox(
            "Agency",
            agencies,
            key="bucket_agency",
            format_func=lambda a: a["agency_id"],
        )
    st.json(bucket_status(cmp_agency["agency_id"], cmp_contact["contact_id"]))

    st.subheader("Recent guardrail blocks")
    with connect() as conn:
        rows = conn.execute(
            """SELECT timestamp, agency_id, contact_id, guardrail, action, reason
               FROM guardrail_log
               ORDER BY timestamp DESC LIMIT 50"""
        ).fetchall()
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True)
    else:
        st.info("No guardrail blocks logged yet.")

# ===========================================================================
# TAB 4: ONLINE METRICS
# ===========================================================================
with tabs[3]:
    st.header("Online Metrics")
    st.caption(
        "We measure business outcomes, not AI vibes. Rep-override-rate is the north-star."
    )

    agencies = list_agencies()
    agency_ids = ["All"] + [a["agency_id"] for a in agencies]
    pick = st.selectbox("Scope", agency_ids, key="metrics_scope")
    scope_id = None if pick == "All" else pick

    m = online_metrics.compute(agency_id=scope_id, window_hours=720)

    col1, col2, col3 = st.columns(3)
    col1.metric("Sent (30d)", m.sent_30d)
    col2.metric(
        "Response rate",
        f"{m.response_rate:.1%}",
        help=f"Target ≥8%. Status: {online_metrics.target_status('response_rate', m.response_rate)}",
    )
    col3.metric(
        "Meeting booked rate",
        f"{m.meeting_booked_rate:.1%}",
        help=f"Target ≥1.5%. Status: {online_metrics.target_status('meeting_booked_rate', m.meeting_booked_rate)}",
    )

    col4, col5, col6 = st.columns(3)
    col4.metric(
        "Unsubscribe rate",
        f"{m.unsubscribe_rate:.2%}",
        help="Target <1%.",
    )
    col5.metric(
        "Spam complaint rate",
        f"{m.spam_complaint_rate:.3%}",
        help="Target <0.08%.",
    )
    col6.metric(
        "★ Rep override rate",
        f"{m.rep_override_rate:.1%}",
        help="Target <15%. North-star: measures actual SDR trust in the AI draft.",
    )

# ===========================================================================
# TAB 5: OFFLINE EVALS
# ===========================================================================
with tabs[4]:
    st.header("Offline Evals")
    st.caption(
        "Run the golden dataset against the deterministic preflight stack. "
        "No deploy without passing gates."
    )

    if st.button("Run eval", type="primary"):
        results = offline_eval.run()
        df = pd.DataFrame(
            [
                {
                    "contact_id": r.contact_id,
                    "agency_id": r.agency_id,
                    "channel": r.channel,
                    "expected": r.expected_decision,
                    "expected_reason": r.expected_block_reason,
                    "actual_ok": r.actual_ok,
                    "actual_reason": r.actual_reason,
                    "passed": r.passed,
                    "note": r.note,
                }
                for r in results
            ]
        )
        st.dataframe(df, use_container_width=True)
        s = offline_eval.summarize(results)
        if s["failed"] == 0:
            st.success(f"All {s['passed']}/{s['total']} cases passed.")
        else:
            st.error(f"{s['failed']} case(s) failed. {s['passed']}/{s['total']} passed.")
    else:
        st.info("Click 'Run eval' to exercise the golden dataset.")

# ===========================================================================
# TAB 6: KILL SWITCH & ADMIN
# ===========================================================================
with tabs[5]:
    st.header("Kill Switch & Admin")
    st.caption(
        "When something goes wrong at 2am, someone needs a single button. "
        "Auto-pause triggers automatically on complaint / unsubscribe / bounce rate."
    )

    agencies = list_agencies()
    st.subheader("Agencies")
    for a in agencies:
        with st.expander(
            f"{a['agency_id']} — {a['name']} — status: {a['status']}",
            expanded=a["status"] == "paused",
        ):
            metrics = kill_switch.get_agency_metrics(a["agency_id"])
            col1, col2, col3 = st.columns(3)
            col1.metric("Spam rate 24h", f"{metrics['spam_complaint_rate_24h']:.3%}")
            col2.metric("Unsub rate 7d", f"{metrics['unsubscribe_rate_7d']:.2%}")
            col3.metric("Bounce rate 24h", f"{metrics['bounce_rate_24h']:.2%}")
            if a.get("pause_reason"):
                st.warning(f"Pause reason: {a['pause_reason']}")

            c1, c2, c3 = st.columns(3)
            if c1.button("Pause", key=f"pause_{a['agency_id']}"):
                pause_agency(a["agency_id"], "manual_admin_pause")
                st.rerun()
            if c2.button("Resume", key=f"resume_{a['agency_id']}"):
                resume_agency(a["agency_id"])
                st.rerun()
            if c3.button("Re-evaluate health", key=f"eval_{a['agency_id']}"):
                st.json(kill_switch.evaluate_agency_health(a["agency_id"]))

    st.subheader("Recent events")
    events = list_recent_events(limit=30)
    if events:
        df = pd.DataFrame(events)[["timestamp", "agency_id", "contact_id", "event_type"]]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No events yet. Run a crew on Tab 1 to populate history.")
