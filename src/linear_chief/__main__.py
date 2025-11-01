"""CLI entry point for Linear Chief of Staff."""

import asyncio
import sys

import click
from tabulate import tabulate

from linear_chief.config import (
    ensure_directories,
    DATABASE_PATH,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_FILE,
)
from linear_chief.utils.logging import setup_logging, get_logger
from linear_chief.orchestrator import BriefingOrchestrator
from linear_chief.scheduling import BriefingScheduler
from linear_chief.storage import (
    init_db,
    get_session_maker,
    get_db_session,
    BriefingRepository,
    MetricsRepository,
)

# Initialize logging system
setup_logging(
    level=LOG_LEVEL,
    format_type=LOG_FORMAT,
    log_file=LOG_FILE,
)
logger = get_logger(__name__)


@click.group()
def cli():
    """Linear Chief of Staff - AI-powered briefing agent."""
    # Ensure directories exist
    ensure_directories()


@cli.command()
def init():
    """Initialize database schema."""
    click.echo("Initializing database...")
    try:
        init_db()
        click.echo(f"✓ Database initialized: {DATABASE_PATH}")
    except Exception as e:
        click.echo(f"✗ Database initialization failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def briefing():
    """Generate and send briefing immediately."""
    click.echo("Generating briefing...")

    orchestrator = BriefingOrchestrator()

    try:
        result = asyncio.run(orchestrator.generate_and_send_briefing())

        if result["success"]:
            click.echo("\n✓ Briefing generated and sent successfully!")
            click.echo(f"  Issues: {result['issue_count']}")
            click.echo(f"  Cost: ${result.get('cost_usd', 0):.4f}")
            click.echo(f"  Duration: {result.get('duration_seconds', 0):.2f}s")
            if result.get("briefing_id"):
                click.echo(f"  Briefing ID: {result['briefing_id']}")
        else:
            click.echo(
                f"\n✗ Briefing failed: {result.get('error', 'Unknown error')}", err=True
            )
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n✗ Briefing failed: {e}", err=True)
        logger.error("Briefing generation failed", exc_info=True)
        sys.exit(1)


@cli.command()
def test():
    """Test connections to all services."""
    click.echo("Testing service connections...\n")

    orchestrator = BriefingOrchestrator()

    try:
        results = asyncio.run(orchestrator.test_connections())

        for service, status in results.items():
            status_icon = "✓" if status else "✗"
            status_text = "OK" if status else "FAILED"
            click.echo(f"{status_icon} {service.capitalize()}: {status_text}")

        all_ok = all(results.values())
        if not all_ok:
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n✗ Connection test failed: {e}", err=True)
        sys.exit(1)


@cli.command()
def start():
    """Start the scheduler for daily briefings."""
    click.echo("Starting briefing scheduler...")

    orchestrator = BriefingOrchestrator()
    scheduler = BriefingScheduler()

    # Define job wrapper for async orchestrator
    def briefing_job():
        """Job wrapper to run async briefing generation."""
        try:
            asyncio.run(orchestrator.generate_and_send_briefing())
        except Exception as e:
            logger.error(f"Scheduled briefing failed: {e}", exc_info=True)

    try:
        scheduler.start(briefing_job)
        next_run = scheduler.get_next_run_time()

        click.echo("✓ Scheduler started successfully!")
        click.echo(f"  Next briefing: {next_run}")
        click.echo("\nPress Ctrl+C to stop...")

        # Keep running
        try:
            while scheduler.is_running():
                asyncio.run(asyncio.sleep(1))
        except KeyboardInterrupt:
            click.echo("\n\nStopping scheduler...")
            scheduler.stop()
            click.echo("✓ Scheduler stopped")

    except Exception as e:
        click.echo(f"\n✗ Scheduler failed: {e}", err=True)
        logger.error("Scheduler failed", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--days", default=7, help="Number of days to look back")
def metrics(days: int):
    """Display metrics and statistics."""
    click.echo(f"Metrics for last {days} days:\n")

    try:
        session_maker = get_session_maker()

        for session in get_db_session(session_maker):
            briefing_repo = BriefingRepository(session)
            metrics_repo = MetricsRepository(session)

            # Get briefing stats
            recent_briefings = briefing_repo.get_recent_briefings(days=days)
            total_cost = briefing_repo.get_total_cost(days=days)

            click.echo("📊 Briefing Statistics:")
            click.echo(f"  Total briefings: {len(recent_briefings)}")
            click.echo(f"  Total cost: ${total_cost:.4f}")

            if recent_briefings:
                avg_cost = total_cost / len(recent_briefings)
                click.echo(f"  Average cost per briefing: ${avg_cost:.4f}")

                sent_count = sum(
                    1 for b in recent_briefings if b.delivery_status == "sent"
                )
                failed_count = sum(
                    1 for b in recent_briefings if b.delivery_status == "failed"
                )

                click.echo(f"  Sent successfully: {sent_count}")
                click.echo(f"  Failed: {failed_count}")

            # Get API cost metrics
            cost_metrics = metrics_repo.get_aggregated_metrics(
                metric_type="api_cost",
                metric_name="anthropic_briefing",
                days=days,
            )

            if cost_metrics["count"] > 0:
                click.echo("\n💰 API Cost Metrics:")
                click.echo(f"  Total API calls: {int(cost_metrics['count'])}")
                click.echo(f"  Total cost: ${cost_metrics['sum']:.4f}")
                click.echo(f"  Average cost: ${cost_metrics['avg']:.4f}")
                click.echo(f"  Min cost: ${cost_metrics['min']:.4f}")
                click.echo(f"  Max cost: ${cost_metrics['max']:.4f}")

            # Recent briefings table
            if recent_briefings:
                click.echo("\n📝 Recent Briefings:")
                table_data = []
                for b in recent_briefings[:10]:  # Show last 10
                    table_data.append(
                        [
                            b.id,
                            b.generated_at.strftime("%Y-%m-%d %H:%M"),
                            b.issue_count,
                            f"${b.cost_usd:.4f}" if b.cost_usd else "N/A",
                            b.delivery_status,
                        ]
                    )

                headers = ["ID", "Generated At", "Issues", "Cost", "Status"]
                click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))

    except Exception as e:
        click.echo(f"\n✗ Failed to fetch metrics: {e}", err=True)
        logger.error("Metrics fetch failed", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option("--days", default=7, help="Number of days to show")
@click.option("--limit", default=10, help="Number of briefings to show")
def history(days: int, limit: int):
    """Show briefing history."""
    click.echo(f"Briefing history (last {days} days, max {limit} entries):\n")

    try:
        session_maker = get_session_maker()

        for session in get_db_session(session_maker):
            briefing_repo = BriefingRepository(session)
            recent_briefings = briefing_repo.get_recent_briefings(days=days)

            if not recent_briefings:
                click.echo("No briefings found.")
                return

            for i, briefing in enumerate(recent_briefings[:limit], 1):
                click.echo(f"\n{'='*60}")
                click.echo(
                    f"Briefing #{briefing.id} - {briefing.generated_at.strftime('%Y-%m-%d %H:%M')}"
                )
                click.echo(f"{'='*60}")
                click.echo(f"Issues: {briefing.issue_count}")
                click.echo(f"Status: {briefing.delivery_status}")
                click.echo(
                    f"Cost: ${briefing.cost_usd:.4f}"
                    if briefing.cost_usd
                    else "Cost: N/A"
                )
                click.echo(f"\nContent:\n{briefing.content[:500]}...")

    except Exception as e:
        click.echo(f"\n✗ Failed to fetch history: {e}", err=True)
        logger.error("History fetch failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
