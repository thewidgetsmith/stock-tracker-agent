"""
Stock Tracker Agent - Main application entry point.

An AI-powered agent that tracks certain stock prices and traders and sends
Telegram notifications when significant price movements or trades occur.
"""

import asyncio
import os
import sys

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from the new package structure
from stock_tracker.agents.handlers import handle_incoming_message, run_research_pipeline
from stock_tracker.core.stock_checker import get_stock_price
from stock_tracker.core.tracker import track_stocks
from stock_tracker.utils.config import ensure_resources_directory, validate_environment
from stock_tracker.webapi.app import app


async def chat_terminal() -> None:
    """Interactive chat mode for testing purposes."""
    print("Chat mode activated. Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Exiting chat.")
            break
        try:
            response = await handle_incoming_message(user_input)
            print(f"Bot: {response}")
        except Exception as e:
            print(f"Error: {e}")


def main() -> None:
    """Main application entry point."""
    # Ensure required directories and files exist
    ensure_resources_directory()

    # Validate environment
    if not validate_environment():
        print(
            "Please set the required environment variables before running the application."
        )
        print(
            "Required variables: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY"
        )
        sys.exit(1)

    if "-test" in sys.argv:
        if "-research" in sys.argv:
            # Research mode for testing specific stock
            try:
                stock_symbol = sys.argv[sys.argv.index("-research") + 1]
                stock_price = get_stock_price(stock_symbol)
                asyncio.run(
                    run_research_pipeline(
                        stock_symbol,
                        stock_price.current_price,
                        stock_price.previous_close,
                    )
                )
            except (IndexError, ValueError) as e:
                print(
                    f"Error: Please provide a valid stock symbol after -research flag. {e}"
                )
                sys.exit(1)
        else:
            # Interactive test mode with frequent stock tracking
            print("Starting test mode with 1-minute stock tracking...")

            scheduler = BackgroundScheduler()
            scheduler.add_job(track_stocks, "interval", minutes=1)
            scheduler.start()

            try:
                asyncio.run(chat_terminal())
            except KeyboardInterrupt:
                print("\nShutting down...")
            finally:
                scheduler.shutdown()
    else:
        # Production mode
        print("Starting Stock Tracker Agent in production mode...")

        minutes = os.getenv("TRACKING_INTERVAL_MINUTES", "60")

        # Schedule stock tracking every hour
        scheduler = BackgroundScheduler()
        scheduler.add_job(track_stocks, "interval", minutes=int(minutes))
        scheduler.start()

        # Start the FastAPI server
        try:
            uvicorn.run(
                "main:app",
                host=os.getenv("ENDPOINT_HOST", "0.0.0.0"),
                port=int(os.getenv("ENDPOINT_PORT", "8080")),
                reload=False,  # Disable reload in production
                log_level="info",
            )
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            scheduler.shutdown()


if __name__ == "__main__":
    main()
