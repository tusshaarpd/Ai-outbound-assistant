"""Four agents + manager LLM. OpenAI-only deploy — no Anthropic dependency.

Role/goal/backstory copy is intentional — it is the product's differentiator
per spec Part 1. Model assignment per agent is centralized in config.py."""
from crewai import Agent, LLM

from config import (
    CREWAI_VERBOSE,
    DRAFTER_MODEL,
    MANAGER_MODEL,
    RESEARCHER_MODEL,
    REVIEWER_MODEL,
    SENDER_MODEL,
)
from tools.brand_voice_tool import BrandVoiceTool
from tools.calendar_tool import CalendarTool
from tools.contact_history_tool import ContactHistoryTool
from tools.crm_tool import CRMReadTool
from tools.email_tool import EmailSendTool
from tools.linkedin_tool import LinkedInProfileTool

# ========== LLM configs (all OpenAI) ==========
researcher_llm = LLM(model=RESEARCHER_MODEL, temperature=0.2)
drafter_llm = LLM(model=DRAFTER_MODEL, temperature=0.7)
reviewer_llm = LLM(model=REVIEWER_MODEL, temperature=0.1)
manager_llm = LLM(model=MANAGER_MODEL, temperature=0.3)
sender_llm = LLM(model=SENDER_MODEL, temperature=0.0)

# ========== 1. RESEARCHER ==========
researcher = Agent(
    role="B2B Sales Researcher",
    goal=(
        "Enrich a prospect record with public data and produce a 5-bullet brief "
        "that a sales rep can read in 15 seconds. Flag low-quality leads honestly."
    ),
    backstory=(
        "You've worked as an SDR research analyst for 10 years. You know what a "
        "sales rep actually needs to personalize outreach — a trigger event, a "
        "specific pain, a real fact about the prospect. You NEVER fabricate "
        "information. When data is missing, you say 'unknown' and move on."
    ),
    tools=[
        CRMReadTool(),
        LinkedInProfileTool(),
        ContactHistoryTool(),
    ],
    llm=researcher_llm,
    allow_delegation=False,
    verbose=CREWAI_VERBOSE,
    max_iter=3,
    memory=True,
)

# ========== 2. DRAFTER ==========
drafter = Agent(
    role="B2B Copywriter",
    goal=(
        "Write a personalized outbound message under 90 words that sounds human, "
        "references a specific fact about the prospect, has one clear ask, and "
        "matches the agency's brand voice exactly."
    ),
    backstory=(
        "You're a senior copywriter who's written outbound for 50+ B2B brands. "
        "You hate em-dashes, 'leverage,' 'unlock,' and 'seamless.' You know that "
        "the first line decides whether the email gets read. You write like a "
        "human, not like ChatGPT."
    ),
    tools=[BrandVoiceTool()],
    llm=drafter_llm,
    allow_delegation=False,
    verbose=CREWAI_VERBOSE,
    max_iter=2,
    memory=True,
)

# ========== 3. REVIEWER ==========
reviewer = Agent(
    role="Compliance and Brand Reviewer",
    goal=(
        "Block any message that violates CAN-SPAM, GDPR, or TCPA. Revise any "
        "message that sounds AI-generated or misses brand voice. Approve only "
        "messages that pass both compliance and quality bars."
    ),
    backstory=(
        "You were a compliance officer at a marketing platform that got fined "
        "$2M for a GDPR violation. That taught you: compliance is binary. One "
        "missed flag destroys deliverability for every other tenant on the "
        "platform. You block first and revise second. You are strict, not lenient."
    ),
    tools=[BrandVoiceTool()],
    llm=reviewer_llm,
    allow_delegation=False,
    verbose=CREWAI_VERBOSE,
    max_iter=2,
    memory=False,  # Each review is stateless for auditability
)

# ========== 4. SENDER ==========
# Sender is a "thin" agent — it mostly calls deterministic tools.
# We keep it as an Agent so CrewAI tracks it in the workflow, but its job
# is to invoke guardrails and the send tool in order. No creativity allowed.
sender = Agent(
    role="Outbound Operations Dispatcher",
    goal=(
        "Execute a send ONLY after every guardrail passes. Rate limits, "
        "opt-out checks, human-in-the-loop gates, kill switch — all green "
        "before any message leaves the system."
    ),
    backstory=(
        "You are the last line of defense before a message hits a real inbox. "
        "You do not write, edit, or improvise. You run through a checklist. "
        "If any check fails, you stop and log the reason. You treat every "
        "send as if the platform's reputation depends on it — because it does."
    ),
    tools=[EmailSendTool(), CalendarTool()],
    llm=sender_llm,
    allow_delegation=False,
    verbose=CREWAI_VERBOSE,
    max_iter=2,
    memory=False,
)
