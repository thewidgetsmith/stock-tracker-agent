"""
Sentinel - Main application entry point.

An AI-powered agent that tracks certain stock prices and traders and sends
Telegram notifications when significant price movements or trades occur.
"""

import asyncio
import os
import sys

import uvicorn
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import from the new package structure
from sentinel.agents.handlers import handle_incoming_message, run_research_pipeline
from sentinel.config.logging import get_logger

# Import configuration system
from sentinel.config.settings import get_settings
from sentinel.core.stock_query import get_stock_price
from sentinel.scheduler import (
    add_politician_tracking_job,
    add_stock_tracking_job,
    list_scheduled_jobs,
    shutdown_scheduler,
    start_scheduler,
)
from sentinel.utils.config import initialize_application, validate_environment


async def chat_terminal() -> None:
    """Interactive chat mode for testing purposes."""
    logger = get_logger(__name__)
    logger.info("Starting interactive chat mode")

    print("Chat mode activated. Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Exiting chat.")
            logger.info("Chat mode ended by user")
            break
        try:
            logger.debug("Processing user input", input=user_input)
            response = await handle_incoming_message(user_input)
            print(f"Bot: {response}")
            logger.debug("Response sent", response=response)
        except Exception as e:
            print(f"Error: {e}")
            logger.error("Error in chat terminal", error=str(e), exc_info=True)
            print(f"Error: {e}")


def main() -> None:
    """Main application entry point."""
    # Initialize application (logging, config, resources)
    initialize_application()

    # Get logger after initialization
    logger = get_logger(__name__)
    logger.info("Starting Sentinel application")

    # Get settings
    settings = get_settings()

    # Validate environment
    if not validate_environment():
        logger.error("Environment validation failed")
        print(
            "Please set the required environment variables before running the application."
        )
        required_vars = [
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "TELEGRAM_AUTH_TOKEN",
            "OPENAI_API_KEY",
            "ENDPOINT_AUTH_TOKEN",
        ]
        print(f"Required variables: {', '.join(required_vars)}")
        sys.exit(1)

    logger.info("Environment validation passed")

    if "-test" in sys.argv:
        if "-research" in sys.argv:
            # Research mode for testing specific stock
            logger.info("Starting research mode")
            try:
                stock_symbol = sys.argv[sys.argv.index("-research") + 1]
                logger.info("Running research pipeline", symbol=stock_symbol)
                stock_price = get_stock_price(stock_symbol)
                asyncio.run(
                    run_research_pipeline(
                        stock_symbol,
                        stock_price.current_price,
                        stock_price.previous_close,
                    )
                )
            except (IndexError, ValueError) as e:
                logger.error("Invalid research command", error=str(e))
                print(
                    f"Error: Please provide a valid stock symbol after -research flag. {e}"
                )
                sys.exit(1)
        else:
            # Interactive test mode with frequent stock tracking
            logger.info("Starting test mode", interval_minutes=1)
            print("Starting test mode with 1-minute stock tracking...")

            # Start scheduler and add tracking jobs
            start_scheduler()
            add_stock_tracking_job(interval_minutes=1)
            add_politician_tracking_job(hour=9)  # Daily at 9 AM UTC
            list_scheduled_jobs()

            try:
                asyncio.run(chat_terminal())
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                print("\nShutting down...")
            finally:
                logger.info("Shutting down scheduler")
                shutdown_scheduler()
    else:
        # Production mode
        logger.info(
            "Starting production mode",
            interval_minutes=settings.tracking_interval_minutes,
            host=settings.endpoint_host,
            port=settings.endpoint_port,
        )
        print("Starting Sentinel in production mode...")

        # Start scheduler and add tracking jobs
        start_scheduler()
        add_stock_tracking_job(interval_minutes=settings.tracking_interval_minutes)
        add_politician_tracking_job(hour=9)  # Daily at 9 AM UTC
        list_scheduled_jobs()

        # Start the FastAPI server
        try:
            uvicorn.run(
                "sentinel.webapi.app:app",
                host=settings.endpoint_host,
                port=settings.endpoint_port,
                reload=settings.api_reload,  # Use configured reload setting
                log_level=settings.api_log_level.lower(),
            )
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            print("\nShutting down...")
        finally:
            logger.info("Shutting down scheduler")
            shutdown_scheduler()


if __name__ == "__main__":
    main()
