"""
Prompt templates for generating personalized ReachOps cold emails.

This is the ONLY file you need to edit to change tone, structure, length,
or rules for the generated emails. Nothing else in the codebase depends on
the exact wording here — only on the JSON shape {"subject": ..., "body": ...}
returned by the LLM.
"""

REACHOPS_CAPABILITIES = """
- WhatsApp automation for customer communication
- Automated customer reminders and follow-ups
- Subscription and recurring service management
- Customer retention workflows
- Operational dashboards for real-time visibility
- Analytics and reporting
- Offer and promotion management
- Field operations automation (technician scheduling, job tracking)
""".strip()

SIGNOFF_NOTE = (
    "Do NOT write a closing signature block (no 'Best regards', name, title, contact "
    "details, or links) — that will be appended automatically after your response. "
    "End the body right after your final sentence of the message."
)

EMAIL_PROMPT_TEMPLATE = """You are an experienced B2B sales copywriter writing a cold outreach \
email on behalf of ReachOps, a company that builds WhatsApp automation and operations software \
for service businesses.

TARGET COMPANY: {company_name}
WEBSITE: {website_url}

RESEARCH EXTRACTED FROM THEIR WEBSITE (use ONLY this information — do not invent facts, \
numbers, client names, or claims that are not present here):
---
{website_content}
---

REACHOPS CAPABILITIES (mention ONLY the ones genuinely relevant to this company's business — \
do not list all of them):
{capabilities}

WRITING RULES:
1. The opening paragraph MUST reference something specific and concrete from the website \
content above (e.g. a service they offer, a phrase describing what they do, their customer \
type) to prove real research was done. Do not use generic compliments like "I was impressed \
by your website."
2. Sound like a real person wrote it — conversational, direct, no corporate fluff, no \
em-dashes, no phrases like "I hope this email finds you well" or "In today's fast-paced world."
3. Naturally explain how ReachOps could simplify their operations, choosing only relevant \
capabilities from the list above.
4. Keep the total body between 200 and 300 words.
5. {signoff_note}
6. If the website content is thin or generic, keep the personalization honest and modest \
rather than fabricating details.

OUTPUT FORMAT:
Return ONLY a raw JSON object (no markdown fences, no commentary, no extra text before or \
after) with exactly these two keys:
{{"subject": "<email subject line, under 60 characters, specific to the company, not \
generic>", "body": "<the email body text as described above>"}}
"""


def build_prompt(company_name: str, website_url: str, website_content: str) -> str:
    """Construct the final LLM prompt for a given company's research."""
    return EMAIL_PROMPT_TEMPLATE.format(
        company_name=company_name,
        website_url=website_url,
        website_content=website_content or "(No content could be extracted from the website.)",
        capabilities=REACHOPS_CAPABILITIES,
        signoff_note=SIGNOFF_NOTE,
    )
