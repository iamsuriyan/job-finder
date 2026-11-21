"""Typer CLI interface for fundwatch."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from fundwatch import __version__

app = typer.Typer(
    name="fundwatch",
    help="Startup Funding Alert Bot - Monitor RSS feeds for startup funding.",
    add_completion=False,
)
console = Console()


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]fundwatch[/bold cyan] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """fundwatch: Startup Funding Alert Bot."""


@app.command()
def run(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Run the monitoring loop forever."""
    from fundwatch.config import load_config
    from fundwatch.db import Database
    from fundwatch.notifiers import build_notifiers
    from fundwatch.scheduler import Scheduler

    try:
        settings = load_config(config_path=config, enforce_secrets=True)
    except Exception as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    configure_logging(settings.log_level)
    db = Database(settings.db_path)
    notifiers = build_notifiers(settings)

    console.print(
        f"[bold green]Starting fundwatch loop (interval={settings.poll_interval_minutes}m, "
        f"db={settings.db_path}, notifiers={len(notifiers)})[/bold green]"
    )
    scheduler = Scheduler(settings=settings, db=db, notifiers=notifiers)
    scheduler.run_forever()


@app.command()
def once(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
    no_bootstrap: bool = typer.Option(
        False, "--no-bootstrap", help="Do not run bootstrap mode even if DB is empty"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print what would be sent without sending notifications"
    ),
) -> None:
    """Run a single cycle and exit (ideal for cron or GitHub Actions)."""
    from fundwatch.config import load_config
    from fundwatch.db import Database
    from fundwatch.notifiers import build_notifiers
    from fundwatch.pipeline import run_cycle

    # For dry-run, do not require secrets to be set
    enforce_secrets = not dry_run
    try:
        settings = load_config(config_path=config, enforce_secrets=enforce_secrets)
    except Exception as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    configure_logging(settings.log_level)
    db = Database(settings.db_path)
    notifiers = [] if dry_run else build_notifiers(settings)

    is_bootstrap = False if no_bootstrap else None

    console.print(
        f"[bold blue]Running cycle (dry_run={dry_run}, bootstrap={is_bootstrap})...[/bold blue]"
    )

    def print_dry_run(msg: str) -> None:
        console.print(
            f"[bold magenta]--- [DRY-RUN ALERT] ---[/bold magenta]\n{msg}\n"
            f"[bold magenta]-----------------------[/bold magenta]"
        )

    stats = run_cycle(
        settings=settings,
        db=db,
        notifiers=notifiers,
        is_bootstrap=is_bootstrap,
        dry_run=dry_run,
        print_callback=print_dry_run if dry_run else None,
    )

    table = Table(title="Poll Cycle Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    table.add_row("Articles Fetched", str(stats.fetched))
    table.add_row("New Articles", str(stats.new))
    table.add_row("Matched Funding Articles", str(stats.matched))
    table.add_row("Notified Articles", str(stats.notified))
    console.print(table)


@app.command(name="check-feeds")
def check_feeds(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Fetch every feed and print status (OK/failed, entry count, latest title)."""
    from fundwatch.config import load_config
    from fundwatch.fetcher import inspect_feed

    try:
        settings = load_config(config_path=config, enforce_secrets=False)
    except Exception as exc:
        console.print(f"[bold red]Failed to load configuration:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold blue]Checking {len(settings.feeds)} feeds...[/bold blue]\n")
    working_count = 0

    for feed in settings.feeds:
        res = inspect_feed(feed, settings.user_agent, timeout=settings.request_timeout_seconds)
        if res["ok"]:
            working_count += 1
            entries_str = f"({res['entries']} entries)"
            console.print(
                f"[bold green]✔ OK[/bold green] [bold]{feed.name}[/bold] {entries_str}\n"
                f"   URL: {feed.url}\n"
                f"   Latest: {res['latest_title'] or 'N/A'}"
            )
        else:
            console.print(
                f"[bold red]✘ FAILED[/bold red] [bold]{feed.name}[/bold]\n"
                f"   URL: {feed.url}\n"
                f"   Error: {res['error']}"
            )
        console.print()

    console.print(f"Summary: [bold]{working_count}/{len(settings.feeds)}[/bold] feeds working.")
    if working_count < 3:
        console.print("[bold red]Warning: Fewer than 3 working feeds detected![/bold red]")
        raise typer.Exit(code=1)


@app.command(name="test-notify")
def test_notify(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Send a test message through every enabled notifier."""
    from fundwatch.config import load_config
    from fundwatch.notifiers import build_notifiers

    try:
        settings = load_config(config_path=config, enforce_secrets=True)
    except Exception as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    notifiers = build_notifiers(settings)
    if not notifiers:
        console.print("[bold yellow]No notifiers are enabled with required secrets.[/bold yellow]")
        raise typer.Exit(code=0)

    console.print(f"Sending test notification to {len(notifiers)} enabled notifier(s)...")
    test_msg = "🧪 fundwatch test alert: notifications are configured and working properly!"

    success = True
    for n in notifiers:
        try:
            n.send_text(test_msg)
            console.print(f"[bold green]✔ Delivered test alert via {n.name}[/bold green]")
        except Exception as exc:
            console.print(f"[bold red]✘ Failed to deliver via {n.name}:[/bold red] {exc}")
            success = False

    if not success:
        raise typer.Exit(code=1)


@app.command(name="list")
def list_articles(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of articles to show"),
    matched_only: bool = typer.Option(
        False, "--matched-only", "-m", help="Show only matched funding articles"
    ),
) -> None:
    """Show recent stored articles."""
    from fundwatch.config import load_config
    from fundwatch.db import Database

    settings = load_config(config_path=config, enforce_secrets=False)
    db = Database(settings.db_path)
    articles = db.get_recent_articles(limit=limit, matched_only=matched_only)

    if not articles:
        console.print("[yellow]No articles stored yet.[/yellow]")
        return

    table = Table(title=f"Recent Articles ({'Matched Only' if matched_only else 'All'})")
    table.add_column("Feed", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Published", style="dim")
    table.add_column("Matched", justify="center")
    table.add_column("Notified", justify="center")

    for a in articles:
        matched_badge = "[green]Yes[/green]" if a.matched else "[dim]No[/dim]"
        notified_badge = "[green]Yes[/green]" if a.notified else "[dim]No[/dim]"
        pub_str = a.published_at.split("T")[0] if a.published_at else "N/A"
        table.add_row(a.feed_name, a.title[:60], pub_str, matched_badge, notified_badge)

    console.print(table)


@app.command()
def export(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
    out: Path = typer.Option(Path("funding.csv"), "--out", "-o", help="Output CSV path"),
) -> None:
    """Export matched articles joined with extractions to CSV."""
    from fundwatch.config import load_config
    from fundwatch.db import Database

    settings = load_config(config_path=config, enforce_secrets=False)
    db = Database(settings.db_path)
    rows = db.get_matched_articles_with_extractions()

    if not rows:
        console.print("[yellow]No matched articles to export.[/yellow]")
        return

    fieldnames = list(rows[0].keys())
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[bold green]✔ Exported {len(rows)} articles to {out}[/bold green]")


@app.command()
def stats(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
) -> None:
    """Show counts per feed and per day."""
    from fundwatch.config import load_config
    from fundwatch.db import Database

    settings = load_config(config_path=config, enforce_secrets=False)
    db = Database(settings.db_path)
    data = db.get_stats()

    # Totals Table
    t_table = Table(title="Overall Database Statistics")
    t_table.add_column("Metric", style="cyan")
    t_table.add_column("Count", style="green")
    t_table.add_row("Total Articles Seen", str(data["total"]))
    t_table.add_row("Matched Funding Rounds", str(data["matched"]))
    t_table.add_row("Alerts Notified", str(data["notified"]))
    console.print(t_table)
    console.print()

    # Per Feed Table
    f_table = Table(title="Articles by Feed")
    f_table.add_column("Feed Name", style="bold cyan")
    f_table.add_column("Articles Count", justify="right")
    for row in data["by_feed"]:
        f_table.add_row(row["feed_name"], str(row["count"]))
    console.print(f_table)
    console.print()

    # Per Day Table
    if data["by_day"]:
        d_table = Table(title="Articles by Day (Last 14 days)")
        d_table.add_column("Date", style="dim")
        d_table.add_column("Count", justify="right")
        for row in data["by_day"]:
            d_table.add_row(row["day"], str(row["count"]))
        console.print(d_table)


@app.command(name="ui")
def ui(
    config: Path = typer.Option(Path("config.yaml"), "--config", "-c", help="Path to config.yaml"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
) -> None:
    """Launch the clean monochrome web dashboard."""
    import uvicorn

    from fundwatch.config import load_config
    from fundwatch.db import Database
    from fundwatch.web.app import create_app

    try:
        settings = load_config(config_path=config, enforce_secrets=False)
    except Exception as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    configure_logging(settings.log_level)
    db = Database(settings.db_path)
    fastapi_app = create_app(settings=settings, db=db)

    console.print(f"[bold green]Starting fundwatch dashboard at http://{host}:{port}[/bold green]")
    uvicorn.run(fastapi_app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()
