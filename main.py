#!/usr/bin/env python3
"""
ReachOps Cold Email Automation Tool — CLI entry point.

Usage:
    python main.py send leads.csv
    python main.py view 12
    python main.py resend 12
    python main.py list
    python main.py stats
"""
import argparse
import asyncio
import csv
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from config import ConfigError, load_config
from core.database import Database
from core.pipeline import run_campaign

console = Console()

REQUIRED_CSV_COLUMNS = {"Company Name", "Website", "Email"}


def read_leads(csv_path: str) -> list[dict]:
    """Read and validate the leads CSV. Expected columns: Company Name, Website, Email."""
    path = Path(csv_path)
    if not path.exists():
        console.print(f"[red]✗ File not found: {csv_path}[/red]")
        sys.exit(1)

    leads = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not REQUIRED_CSV_COLUMNS.issubset(set(reader.fieldnames or [])):
            console.print(
                f"[red]✗ CSV must contain columns: {', '.join(REQUIRED_CSV_COLUMNS)}[/red]\n"
                f"Found: {reader.fieldnames}"
            )
            sys.exit(1)

        for row in reader:
            company = (row.get("Company Name") or "").strip()
            website = (row.get("Website") or "").strip()
            email = (row.get("Email") or "").strip()
            if company and website and email:
                leads.append({"company": company, "website": website, "email": email})
            else:
                console.print(f"[yellow]⚠ Skipping incomplete row: {row}[/yellow]")

    return leads


def cmd_send(args: argparse.Namespace) -> None:
    config = load_config()
    leads = read_leads(args.csv_path)

    if not leads:
        console.print("[yellow]No valid leads found in CSV.[/yellow]")
        return

    console.print(f"[bold]Loaded {len(leads)} lead(s) from {args.csv_path}[/bold]")
    db = Database(config.db_path)
    asyncio.run(run_campaign(config, db, leads))
    console.print("\n[bold green]Campaign complete.[/bold green]")


def cmd_view(args: argparse.Namespace) -> None:
    config = load_config()
    db = Database(config.db_path)
    log = db.get_log(args.log_id)

    if not log:
        console.print(f"[red]✗ No log found with id {args.log_id}[/red]")
        return

    console.print(f"\n[bold]Company:[/bold] {log['company_name']}")
    console.print(f"[bold]Website:[/bold] {log['website']}")
    console.print(f"[bold]Recipient:[/bold] {log['recipient']}")
    console.print(f"[bold]Status:[/bold] {log['status']}")
    console.print(f"[bold]Time Sent:[/bold] {log['time_sent']}")
    if log["error"]:
        console.print(f"[bold red]Error:[/bold red] {log['error']}")
    console.print(f"\n[bold]Subject:[/bold] {log['subject']}\n")
    console.print(f"[bold]Body:[/bold]\n{log['body']}\n")


def cmd_resend(args: argparse.Namespace) -> None:
    config = load_config()
    db = Database(config.db_path)
    log = db.get_log(args.log_id)

    if not log:
        console.print(f"[red]✗ No log found with id {args.log_id}[/red]")
        return
    if not log["subject"] or not log["body"]:
        console.print("[red]✗ This log has no generated email content to resend.[/red]")
        return

    from core.email_sender import EmailSendError, send_email

    async def _resend() -> None:
        console.print(f"[bold cyan]Resending email to {log['recipient']}...[/bold cyan]")
        try:
            await send_email(config, log["recipient"], log["subject"], log["body"])
            db.update_log(args.log_id, "sent", "")
            console.print("[green]✓ Email resent successfully[/green]")
        except EmailSendError as exc:
            db.update_log(args.log_id, "failed", str(exc))
            console.print(f"[red]✗ Failed to resend email[/red]\n[dim]Reason:[/dim] {exc}")

    asyncio.run(_resend())


def cmd_list(args: argparse.Namespace) -> None:
    config = load_config()
    db = Database(config.db_path)
    logs = db.list_logs(limit=args.limit)

    if not logs:
        console.print("[yellow]No logs found.[/yellow]")
        return

    table = Table(title="Email Logs")
    table.add_column("ID", style="dim")
    table.add_column("Company")
    table.add_column("Recipient")
    table.add_column("Status")
    table.add_column("Time Sent")

    for log in logs:
        status_style = {"sent": "green", "failed": "red"}.get(log["status"], "yellow")
        table.add_row(
            str(log["id"]),
            log["company_name"],
            log["recipient"],
            f"[{status_style}]{log['status']}[/{status_style}]",
            (log["time_sent"] or "-"),
        )
    console.print(table)


def cmd_stats(args: argparse.Namespace) -> None:
    config = load_config()
    db = Database(config.db_path)
    stats = db.stats()

    console.print(f"\n[bold]Total emails processed:[/bold] {stats['total']}")
    console.print(f"[green]Sent: {stats['sent']}[/green]")
    console.print(f"[red]Failed: {stats['failed']}[/red]")
    console.print(f"[bold]Success rate:[/bold] {stats['success_rate']}%\n")

    if stats["by_company"]:
        table = Table(title="Emails per Company")
        table.add_column("Company")
        table.add_column("Count")
        for row in stats["by_company"]:
            table.add_row(row["company_name"], str(row["c"]))
        console.print(table)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py", description="ReachOps AI-powered cold email automation tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_send = subparsers.add_parser("send", help="Run a cold email campaign from a CSV file")
    p_send.add_argument("csv_path", help="Path to the leads CSV (Company Name, Website, Email)")
    p_send.set_defaults(func=cmd_send)

    p_view = subparsers.add_parser("view", help="View the full generated email for a log id")
    p_view.add_argument("log_id", type=int)
    p_view.set_defaults(func=cmd_view)

    p_resend = subparsers.add_parser("resend", help="Resend a previously generated email")
    p_resend.add_argument("log_id", type=int)
    p_resend.set_defaults(func=cmd_resend)

    p_list = subparsers.add_parser("list", help="List recent email logs")
    p_list.add_argument("--limit", type=int, default=50, help="Max rows to show (default 50)")
    p_list.set_defaults(func=cmd_list)

    p_stats = subparsers.add_parser("stats", help="Show campaign statistics")
    p_stats.set_defaults(func=cmd_stats)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except ConfigError as exc:
        console.print(f"[red]✗ Configuration error: {exc}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001 - top-level safety net for a CLI tool
        console.print(f"[red]✗ Unexpected error: {exc}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
