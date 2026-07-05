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

EMAIL_PROMPT_TEMPLATE = """You are an experienced B2B SaaS founder writing a personalized cold outreach \
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

WRITING Rules:

1. Mention two specific service, workflow, customer type, or operational detail from their website in the first sentence. Make it obvious the email was researched specifically for them.
2. Never flatter unnecessarily.
3. Write like a founder reaching out to another business owner.
4. Keep the email between 220-280 words. Make it feel substantive and informative rather than brief.
5. Use up to 3 short paragraphs of prose, plus a short bullet list. Separate paragraphs with a single blank line so the email looks clean and easy to read.
6. Use bullet points for ReachOps benefits. Never mention more than four bullet points. Use Unicode bullet points (•) for every bullet.
Choose only the most relevant capabilities.
7. Mention capabilities that actually fit their business and explain why they matter operationally for this company.
8. In the body, include a brief but clear explanation of what ReachOps is and how it helps service businesses run customer communication and operations more smoothly. Explicitly mention ReachOps capabilities such as WhatsApp automation, customer reminders, and operational visibility.
9. Each bullet should mention one ReachOps capability followed by the practical business benefit for that company.
10. Keep every sentence short, but make the overall message fuller and more useful.
11. Avoid buzzwords and corporate language.
12. Make it feel skimmable while still sounding informative and thoughtful.
13. Finish with one friendly sentence/CTA inviting them for a quick 15-minute demo or introductory call if they think it could be useful.
14. Do not invent information not present on their website.
15. Never use phrases like:

"I hope you're doing well"

"I hope this email finds you well"

"I came across your website"

"I was impressed by"

"In today's fast-paced world"

"I believe"

"I wanted to reach out"

"Leverage"

"Seamlessly"

"Revolutionize"

"Transform your business"

"Game changer"
16. {signoff_note}

Preferred structure:

Paragraph 1
- Mention something specific from their website.
- Transition naturally into why you're reaching out.

Paragraph 2

Use a natural transition such as:

"Based on what I saw, ReachOps could help with:"

or

"I think there are a few areas where ReachOps could add value:"
Present the benefits as a short bullet list with Unicode bullets (•), separated by a single blank line before and after the list if needed.

• ...
• ...
• ...
• ...

Paragraph 3

End with one friendly sentence asking if they'd be open to a quick 15-minute demo or call next week. Keep it conversational and avoid sounding pushy.

OUTPUT FORMAT:
Return ONLY a raw JSON object (no markdown fences, no commentary, no extra text before or \
after) with exactly these two keys.
The response must be valid JSON.
Use double quotes for keys and string values.
Do not include literal newline characters inside the body string.
Use \\n\\n for paragraph breaks inside the body and \\n• for bullet points inside the body.
Example shape:
{{"subject": "Short, specific subject line", "body": "First paragraph\\n\\nSecond paragraph\\n\\n• Bullet one\\n• Bullet two"}}

Subject requirements:
- At least 5 words.
- Under 70 characters.
- Specific to the company.
- Strong and direct.
- Sound like a real email from a founder.
- Avoid generic sales phrases.
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
