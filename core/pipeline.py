"""
Per-company pipeline: research the website, generate a personalized email,
send it, and log the result — with Rich console output matching the
required terminal UX.
"""
import asyncio

from rich.console import Console
from rich.panel import Panel

from config import Config
from core.database import Database
from core.email_sender import EmailSendError, build_signature, send_email
from core.llm import LLMError
from core.scraper import scrape_website

console = Console()

MAX_SEND_RETRIES = 2
RETRY_DELAY_SECONDS = 2


async def process_company(config: Config, db: Database, llm_provider, company_name: str,
                           website: str, recipient: str, semaphore: asyncio.Semaphore) -> None:
    """Run the full research -> generate -> send -> log pipeline for one company."""
    async with semaphore:
        console.print(f"\n[bold cyan]Researching {company_name}...[/bold cyan]")

        scraped = await scrape_website(website)
        if not scraped.success:
            console.print(f"[red]✗ Could not analyze website[/red]  ({scraped.error})")
            await asyncio.to_thread(
                db.insert_log, company_name, website, recipient, "", "", "failed",
                f"Website research failed: {scraped.error}",
            )
            console.print("-" * 40)
            return
        console.print("[green]✓ Website analyzed[/green]")

        console.print("[bold cyan]Generating personalized email...[/bold cyan]")
        try:
            result = await llm_provider.generate_email(company_name, website, scraped.content)
        except LLMError as exc:
            console.print(f"[red]✗ Failed to generate email[/red]  ({exc})")
            await asyncio.to_thread(
                db.insert_log, company_name, website, recipient, "", "", "failed",
                f"LLM generation failed: {exc}",
            )
            console.print("-" * 40)
            return

        subject = result["subject"]
        body = result["body"] + build_signature(config)
        console.print("[green]✓ Subject generated[/green]")
        console.print("[green]✓ Body generated[/green]")

        console.print("[bold cyan]Sending email...[/bold cyan]")
        log_id = await asyncio.to_thread(
            db.insert_log, company_name, website, recipient, subject, body, "pending",
        )

        last_error = ""
        for attempt in range(1, MAX_SEND_RETRIES + 1):
            try:
                await send_email(config, recipient, subject, body)
                await asyncio.to_thread(db.update_log, log_id, "sent", "")
                console.print("[green]✓ Email sent successfully[/green]\n")
                console.print(Panel.fit(recipient, title="Recipient", border_style="blue"))
                console.print(Panel.fit(subject, title="Subject", border_style="blue"))
                console.print(f"\n[dim]Type 'view {log_id}' to display the full generated email.[/dim]")
                console.print("-" * 40)
                return
            except EmailSendError as exc:
                last_error = str(exc)
                console.print(f"[red]✗ Failed to send email[/red]\n[dim]Reason:[/dim] {last_error}")
                if attempt < MAX_SEND_RETRIES:
                    console.print("[yellow]Retrying...[/yellow]")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)

        await asyncio.to_thread(db.update_log, log_id, "failed", last_error)
        console.print(f"[dim]Log id: {log_id}[/dim]")
        console.print("-" * 40)


async def run_campaign(config: Config, db: Database, leads: list) -> None:
    """Run the pipeline for every lead, respecting MAX_CONCURRENCY."""
    from core.llm import get_llm_provider

    llm_provider = get_llm_provider(config)
    semaphore = asyncio.Semaphore(max(1, config.max_concurrency))

    tasks = [
        process_company(
            config, db, llm_provider,
            lead["company"], lead["website"], lead["email"], semaphore,
        )
        for lead in leads
    ]
    await asyncio.gather(*tasks)
