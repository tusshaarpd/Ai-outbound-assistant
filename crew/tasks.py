"""Task definitions. Outputs are JSON so downstream code can parse deterministically."""
from crewai import Task

from crew.agents import drafter, researcher, reviewer, sender


def build_tasks(contact_id: str, agency_id: str, channel: str = "email") -> list[Task]:
    """Build fresh tasks per kickoff so inputs are bound correctly."""

    research_task = Task(
        description=(
            f"Research prospect with contact_id='{contact_id}' for agency_id='{agency_id}'. "
            "Use the CRM tool to read contact data. Use the LinkedIn tool for public profile. "
            "Use the ContactHistory tool to check prior outreach. "
            "Flag if the contact is a job-seeker, student, or clearly not a decision-maker. "
            "Output a 5-bullet brief plus 2 personalization hooks plus a confidence score 0-1."
        ),
        expected_output=(
            "A JSON object with keys: role_context, trigger_event, likely_pain, "
            "personalization_hooks (list of 2 strings), confidence (float 0-1), "
            "quality_flags (list of strings)."
        ),
        agent=researcher,
    )

    draft_task = Task(
        description=(
            f"Using the prospect brief from the Researcher, write a {channel} message "
            f"on behalf of agency_id='{agency_id}'. Use the BrandVoice tool to load "
            "the agency's tone profile. Maximum 90 words body, 50 characters subject. "
            "First line MUST reference a specific fact from the personalization hooks. "
            "Include exactly ONE ask. Do NOT add opt-out language — that is injected later. "
            "Do NOT use em-dashes, 'leverage,' 'unlock,' 'seamless,' 'elevate,' 'robust.'"
        ),
        expected_output=(
            "A JSON object with keys: subject (str, max 50 chars), body (str, max 90 words), "
            "rationale (str explaining why this angle works for this prospect)."
        ),
        agent=drafter,
        context=[research_task],
    )

    review_task = Task(
        description=(
            f"Review the drafted message for contact_id='{contact_id}'. "
            "Check in this order: "
            "1) COMPLIANCE: CAN-SPAM opt-out language check, GDPR consent basis check "
            "for EU contacts, TCPA consent for SMS/voice. Any failure = BLOCK. "
            "2) QUALITY: specific first line, single ask, under 90 words, no AI-tells. "
            "Failure = REVISE (provide revised version). "
            "3) BRAND FIT: tone matches brand_voice profile. Failure = REVISE."
        ),
        expected_output=(
            "A JSON object with keys: decision ('approve'|'revise'|'block'), "
            "compliance_flags (list), quality_flags (list), brand_flags (list), "
            "revised_version (str or null), block_reason (str or null)."
        ),
        agent=reviewer,
        context=[research_task, draft_task],
    )

    send_task = Task(
        description=(
            f"If and only if the Reviewer's decision is 'approve', send the message. "
            "BEFORE sending, run these guardrails in order: "
            "1) rate_limiter.can_send(agency_id, contact_id) "
            "2) opt_out.is_opted_out(contact_id) "
            "3) human_review_gate.is_required(agency_id, messages_sent) "
            "4) kill_switch.is_paused(agency_id) "
            "5) opt_out.inject(body, channel) "
            "If ANY guardrail blocks, do NOT send. Log the reason. Return the status. "
            "If the Reviewer's decision was 'block' or 'revise', do NOT send — report the decision."
        ),
        expected_output=(
            "A JSON object with keys: status ('sent'|'deferred'|'blocked'|"
            "'pending_human_review'|'skipped_by_reviewer'), "
            "reason (str), message_id (str or null), timestamp (ISO8601 str)."
        ),
        agent=sender,
        context=[research_task, draft_task, review_task],
    )

    return [research_task, draft_task, review_task, send_task]
