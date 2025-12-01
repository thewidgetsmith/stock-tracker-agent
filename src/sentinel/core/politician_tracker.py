"""Politician trading tracking functionality and automated monitoring."""

import asyncio
from datetime import date, datetime
from typing import List

from ..agents.handlers import run_politician_research_pipeline
from ..config.logging import get_logger
from ..config.settings import get_settings
from ..ormdb.repositories import (
    PoliticianActivityRepository,
    TrackedPoliticianRepository,
)
from ..services.congressional import CongressionalService

logger = get_logger(__name__)


def get_tracked_politicians() -> List[str]:
    """Get the current list of tracked politicians."""
    with TrackedPoliticianRepository() as repo:
        tracked_politicians = repo.get_all_tracked_politicians()

    politician_names = []
    for tracked in tracked_politicians:
        if hasattr(tracked, "politician") and tracked.politician:
            politician_names.append(tracked.politician.name)

    return politician_names


async def fetch_politician_trades(politician_name: str) -> bool:
    """
    Fetch latest trades for a politician from Quiver API.

    Args:
        politician_name: Name of the politician

    Returns:
        True if new trades were found, False otherwise
    """
    settings = get_settings()

    if not settings.quiver_api_token:
        logger.warning("Quiver API token not configured, skipping API fetch")
        return False

    try:
        logger.info(f"Fetching trades for {politician_name}")
        service = CongressionalService(settings.quiver_api_token)

        # Fetch trades from the last 7 days to catch recent activity
        trades = await service.get_congressional_trades(
            representative=politician_name, days_back=7, save_to_db=True
        )

        if trades:
            logger.info(f"Found {len(trades)} recent trades for {politician_name}")
            return True
        else:
            logger.info(f"No recent trades found for {politician_name}")
            return False

    except Exception as e:
        logger.error(f"Error fetching trades for {politician_name}: {e}")
        return False


def should_trigger_research(politician_name: str) -> bool:
    """
    Determine if we should trigger research based on new activities.

    Args:
        politician_name: Name of the politician

    Returns:
        True if research should be triggered
    """
    with PoliticianActivityRepository() as activity_repo:
        # Get activities from the last 2 days that haven't been analyzed
        recent_activities = activity_repo.get_recent_activities_by_politician(
            politician_name, days=2
        )

        # Check for unanalyzed activities
        unanalyzed = [
            activity for activity in recent_activities if not activity.is_analyzed
        ]

        if unanalyzed:
            logger.info(
                f"Found {len(unanalyzed)} unanalyzed activities for {politician_name}"
            )
            return True

        return False


async def track_politicians() -> None:
    """
    Main politician tracking function that fetches trades and triggers research.

    This function:
    1. Gets list of tracked politicians
    2. Fetches latest trades from Quiver API
    3. Triggers research pipeline for new trading activity
    """
    logger.info("Starting politician tracking...")

    tracked_politicians = get_tracked_politicians()
    logger.info(
        f"Tracking {len(tracked_politicians)} politicians: {tracked_politicians}"
    )

    if not tracked_politicians:
        logger.info("No politicians to track")
        return

    for politician_name in tracked_politicians:
        try:
            logger.info(f"Processing {politician_name}")

            # Fetch latest trades from API
            new_trades_found = await fetch_politician_trades(politician_name)

            # Check if we should trigger research
            if should_trigger_research(politician_name):
                logger.info(f"Triggering research pipeline for {politician_name}")

                # Run research pipeline
                await run_politician_research_pipeline(politician_name)

                # Mark activities as analyzed
                await mark_activities_analyzed(politician_name)
            else:
                logger.info(f"No research needed for {politician_name}")

        except Exception as e:
            logger.error(f"Error tracking {politician_name}: {e}")


async def mark_activities_analyzed(politician_name: str) -> None:
    """Mark recent activities as analyzed to prevent duplicate research."""
    try:
        with PoliticianActivityRepository() as activity_repo:
            recent_activities = activity_repo.get_recent_activities_by_politician(
                politician_name, days=2
            )

            for activity in recent_activities:
                if not activity.is_analyzed:
                    activity_repo.mark_activity_analyzed(
                        activity.id, analysis_notes=f"Analyzed on {datetime.now()}"
                    )

        logger.info(f"Marked activities as analyzed for {politician_name}")

    except Exception as e:
        logger.error(f"Error marking activities as analyzed for {politician_name}: {e}")


def run_politician_tracking_sync():
    """
    Synchronous wrapper for the async politician tracking function.

    This function is used by the scheduler to run the async tracking job.
    """
    import asyncio

    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(track_politicians())
        loop.close()
        logger.info("Politician tracking job completed successfully")
    except Exception as e:
        logger.error(f"Error in politician tracking job: {e}")


def run_politician_research_sync(politician_name: str):
    """
    Synchronous wrapper for running research on a specific politician.

    This function is used by the scheduler to run individual research jobs.
    """
    import asyncio

    try:
        # Run the async research pipeline
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Fetch latest trades first
        loop.run_until_complete(fetch_politician_trades(politician_name))

        # Run research pipeline
        loop.run_until_complete(run_politician_research_pipeline(politician_name))

        # Mark activities as analyzed
        loop.run_until_complete(mark_activities_analyzed(politician_name))

        loop.close()
        logger.info(
            f"Politician research job for {politician_name} completed successfully"
        )
    except Exception as e:
        logger.error(f"Error in politician research job for {politician_name}: {e}")
