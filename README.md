# ReachOps Cold Email Automation Tool

A terminal-only, AI-powered cold email tool for ReachOps. For every company in a
CSV file it:

1. **Researches** the company's website (Home/About/Services/Solutions/Contact),
   stripping out nav/header/footer/cookie-banner noise.
2. **Generates** a personalized, non-generic-sounding cold email using an LLM
   (OpenAI, Anthropic, or Gemini — your choice).
3. **Sends** it via SMTP (Gmail or any custom SMTP server).
4. **Logs** everything to a local SQLite database, viewable/queryable from the CLI.

No frontend, no server — just `python main.py <command>`.

---

## 1. Project structure

```
reachops-cold-email/
├── main.py                # CLI entry point (send / view / resend / list / stats)
├── config.py               # Loads & validates .env configuration
├── prompts.py               # Email-generation prompt template — edit this to change tone/rules
├── core/
│   ├── models.py            # Lead / ScrapedSite / GeneratedEmail dataclasses
│   ├── scraper.py            # Website research (requests + BeautifulSoup)
│   ├── llm.py                # LLM provider abstraction (OpenAI / Anthropic / Gemini)
│   ├── email_sender.py        # Async SMTP sending (aiosmtplib) + fixed signature block
│   ├── database.py             # SQLite logging layer
│   └── pipeline.py              # Orchestrates research -> generate -> send -> log per company
├── requirements.txt
├── .env.example
└── leads.sample.csv         # Example input file
```

---

## 2. Setup

### 2.1 Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `openai`, `anthropic`, or `gemini` |
| `LLM_API_KEY` | API key for the chosen provider |
| `LLM_MODEL` | Optional — model name override |
| `SMTP_HOST` / `SMTP_PORT` | e.g. `smtp.gmail.com` / `587` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP login (see Gmail note below) |
| `SENDER_NAME` / `SENDER_EMAIL` | The "From" identity used to send |
| `MAX_CONCURRENCY` | How many companies to process in parallel (default `1`) |
| `DB_PATH` | SQLite file path (default `reachops_outreach.db`) |

The contact block that appears at the bottom of **every** email (Vyakhya Goyal,
Product Manager | ReachOps, portfolio link, support email, phone) is baked in
as the default in `config.py` and appended in code (not left to the LLM), so it's
always accurate. You can override it via `.env` if these details ever change —
see the `CONTACT_*` variables in `.env.example`.

#### Using Gmail as your SMTP server

Gmail requires an **App Password**, not your normal login password:
1. Enable 2-Step Verification on your Google account.
2. Go to [Google Account → Security → App Passwords](https://myaccount.google.com/apppasswords).
3. Generate a password for "Mail" and use it as `SMTP_PASSWORD`.

---

## 3. Input CSV format

```csv
Company Name,Website,Email
AKS Facilities,https://aksfacilities.in,contact@aksfacilities.in
ABC Cleaning,https://abc.com,info@abc.com
```

The three column headers (`Company Name`, `Website`, `Email`) are required. Extra
columns are ignored; incomplete rows are skipped with a warning.

---

## 4. Usage

```bash
# Run a full campaign from a CSV file
python main.py send leads.csv

# View the full generated email for a given log id
python main.py view 12

# Resend a previously generated email (reuses the same subject/body, no re-research)
python main.py resend 12

# List recent email logs (default limit 50)
python main.py list
python main.py list --limit 100

# Show aggregate campaign statistics
python main.py stats
```

### Example terminal output

```
Researching AKS Facilities...
✓ Website analyzed
Generating personalized email...
✓ Subject generated
✓ Body generated
Sending email...
✓ Email sent successfully

╭─ Recipient ────────────────╮
│ contact@aksfacilities.in   │
╰────────────────────────────╯
╭─ Subject ────────────────────────────────────────────╮
│ Can ReachOps simplify operations at AKS Facilities?   │
╰────────────────────────────────────────────────────────╯

Type 'view 12' to display the full generated email.
----------------------------------------
```

On failure:

```
✗ Failed to send email
Reason: SMTP Authentication Error: ...
Retrying...
```

Each company gets **up to 2 send attempts** with a short delay between them
before being marked `failed` in the database. Research/generation failures are
also logged (with `status = failed` and a descriptive `error`), so nothing
silently disappears — check `python main.py list` / `stats` afterward.

---

## 5. How it works

### 5.1 Research (`core/scraper.py`)
- Fetches the homepage, then discovers same-domain links whose href/text match
  keywords like `about`, `service`, `solution`, `contact` (up to 5 pages total).
- Strips `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, and common
  cookie-banner elements before extracting visible text.
- Combined text is capped at ~6000 characters to keep LLM prompts efficient.
- If nothing can be fetched or no meaningful text is found, the company is
  logged as `failed` and skipped — **no content is ever fabricated**.

### 5.2 Generation (`core/llm.py` + `prompts.py`)
- The prompt in `prompts.py` instructs the model to:
  - Reference something *specific* from the scraped content in the opening line.
  - Only mention ReachOps capabilities that are actually relevant.
  - Stay 200–300 words, sound human, avoid clichés.
  - Return **only** raw JSON: `{"subject": "...", "body": "..."}`.
  - Never write its own sign-off — the real contact block is appended in code.
- `core/llm.py` is a small provider-abstraction layer. Switching providers is a
  one-line `.env` change (`LLM_PROVIDER=openai|anthropic|gemini`); adding a new
  provider means subclassing `BaseLLMProvider` and registering it in
  `get_llm_provider()`.

### 5.3 Sending (`core/email_sender.py`)
- Uses `aiosmtplib` for true async SMTP delivery (works with Gmail's STARTTLS
  flow on port 587, or any custom SMTP server).
- The fixed ReachOps signature block is appended to the LLM-generated body
  before sending, guaranteeing correct contact details every time.

### 5.4 Logging (`core/database.py`)
SQLite table `email_logs`:

| Column | Description |
|---|---|
| `id` | Auto-increment primary key |
| `company_name`, `website`, `recipient` | Lead info |
| `subject`, `body` | The generated (and sent) email |
| `time_sent` | UTC ISO timestamp of the last attempt |
| `status` | `sent`, `failed`, or `pending` |
| `error` | Error message if applicable |

### 5.5 Concurrency
`core/pipeline.py` processes companies concurrently (bounded by
`MAX_CONCURRENCY`), using `asyncio.to_thread` for blocking calls (scraping,
SQLite) and native async for SMTP and LLM SDK calls. Default concurrency is
`1` for clean, non-interleaved terminal logs — raise it in `.env` once you're
comfortable reading interleaved output for faster campaigns.

---

## 6. Customization

- **Change the prompt / tone / word count / rules** → edit `prompts.py` only.
- **Add a new ReachOps capability to consider** → add it to
  `REACHOPS_CAPABILITIES` in `prompts.py`.
- **Change which pages get scraped** → edit `KEYWORDS` / `MAX_PAGES` in
  `core/scraper.py`.
- **Add a new LLM provider** → subclass `BaseLLMProvider` in `core/llm.py` and
  register it in `get_llm_provider()`.
- **Change retry behavior** → edit `MAX_SEND_RETRIES` / `RETRY_DELAY_SECONDS`
  in `core/pipeline.py`.

---

## 7. Notes & limitations

- API keys and SMTP credentials are read only from `.env` — never hardcoded,
  never logged.
- The tool does not fabricate company information: if a website can't be
  reached or yields no usable text, that company is logged as `failed` rather
  than guessed at.
- `resend` re-sends the exact stored subject/body — it does not re-scrape or
  regenerate. To send a fresh, re-researched email, just run `send` again with
  that company's CSV row.
#   A I - p o w e r e d - c o l d - e m a i l - a u t o m a t i o n - t o o l  
 