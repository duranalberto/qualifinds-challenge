import logging

from app.core.llm import get_llm
from app.services.planner_state import ExtractedIntent, PlannerState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a workflow intent extractor. Given a natural language instruction, "
    "extract structured intent.\n\n"
    "Valid trigger_type values: new_lead, deal_closed, account_updated, "
    "invoice_created, contract_expiring, support_ticket, unknown\n\n"
    "Valid integrations values: hubspot, salesforce, sap, zendesk, jira, slack, stripe, gmail\n\n"
    "Valid action_intents values: enrich, notify, create_task, escalate, "
    "update_stage, create_issue, assign, charge_customer, send_email, create_invoice, renew\n\n"
    "Rules:\n"
    '- Set trigger_type to "unknown" if you cannot determine it\n'
    "- Set threshold to null if no numeric condition is present\n"
    "- Only include integrations explicitly mentioned in the instruction\n"
    '- workflow_name should be a human-readable name like "Large Lead Enrichment"\n\n'
    "Return the structured intent as requested."
)


async def extract_intent_node(state: PlannerState) -> PlannerState:
    llm = get_llm()
    structured_llm = llm.with_structured_output(ExtractedIntent)
    try:
        messages = [
            ("system", SYSTEM_PROMPT),
            ("human", state["instruction"]),
        ]
        result = await structured_llm.ainvoke(messages)
        return {**state, "intent": result}
    except Exception as exc:
        logger.warning("extract_intent_node failed, continuing with fallback: %s", exc)
        return {**state, "intent": None}
