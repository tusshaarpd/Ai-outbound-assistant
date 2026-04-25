"""Assemble the hierarchical crew and expose a single run_outbound() entrypoint.

Also provides a deterministic pre-flight (`preflight_guardrails`) that runs the
guardrail stack before the crew kickoff so the demo can hard-block opted-out
contacts, rate-limited contacts, and paused agencies without spending LLM calls.
"""
from crewai import Crew, Process

from config import CREWAI_VERBOSE, HAS_OPENAI
from crew.agents import drafter, manager_llm, researcher, reviewer, sender
from crew.tasks import build_tasks
from guardrails.preflight import preflight_guardrails

__all__ = ["build_crew", "run_outbound", "preflight_guardrails"]


def build_crew(contact_id: str, agency_id: str, channel: str = "email") -> Crew:
    tasks = build_tasks(contact_id, agency_id, channel)
    # CrewAI's built-in memory uses ChromaDB with an OpenAI embedder by default.
    # Without an OpenAI key, Chroma init fails — disable memory in that case.
    return Crew(
        agents=[researcher, drafter, reviewer, sender],
        tasks=tasks,
        process=Process.hierarchical,
        manager_llm=manager_llm,
        memory=HAS_OPENAI,
        cache=True,
        max_rpm=30,
        verbose=CREWAI_VERBOSE,
    )


def run_outbound(contact_id: str, agency_id: str, channel: str = "email") -> dict:
    """Single-contact end-to-end entrypoint used by app.py and smoke tests."""
    pre = preflight_guardrails(contact_id, agency_id, channel)
    if not pre["ok"]:
        return {
            "status": "blocked",
            "blocked_at": pre["stage"],
            "reason": pre["reason"],
            "contact_id": contact_id,
            "agency_id": agency_id,
        }

    crew = build_crew(contact_id, agency_id, channel)
    result = crew.kickoff(
        inputs={"contact_id": contact_id, "agency_id": agency_id, "channel": channel}
    )
    return {
        "status": "completed",
        "blocked_at": None,
        "reason": None,
        "human_review_required": pre["human_review_required"],
        "contact_id": contact_id,
        "agency_id": agency_id,
        "crew_output": str(result),
    }


if __name__ == "__main__":
    # Smoke test: happy path contact
    import json

    out = run_outbound("c_001", "acme_gyms", "email")
    print(json.dumps(out, indent=2, default=str))
