"""Database migration utilities for moving data from JSON to SQLAlchemy."""

import json
from pathlib import Path
from typing import Dict, List

from .database import create_tables, get_session_sync
from .repositories import AlertHistoryRepository, TrackedStockRepository


def migrate_json_to_database():
    """Migrate data from JSON files to the database."""
    print("Starting database migration...")

    # Create tables
    create_tables()
    print("Created database tables")

    # Get paths to JSON files
    resources_dir = Path(__file__).parent.parent.parent.parent / "resources"
    tracker_file = resources_dir / "tracker_list.json"
    alert_file = resources_dir / "alert_history.json"

    with get_session_sync() as session:
        # Migrate tracker list
        if tracker_file.exists():
            print(f"Migrating tracker list from {tracker_file}")
            migrate_tracker_list(session, tracker_file)

        # Migrate alert history
        if alert_file.exists():
            print(f"Migrating alert history from {alert_file}")
            migrate_alert_history(session, alert_file)

    print("Database migration completed!")


def migrate_tracker_list(session, tracker_file: Path):
    """Migrate tracker_list.json to TrackedStock table."""
    try:
        with open(tracker_file, "r") as f:
            stock_symbols = json.load(f)

        with TrackedStockRepository(session) as stock_repo:
            for symbol in stock_symbols:
                stock_repo.add_stock(symbol)
                print(f"Added stock: {symbol}")

        print(f"Migrated {len(stock_symbols)} stocks")

    except Exception as e:
        print(f"Error migrating tracker list: {e}")


def migrate_alert_history(session, alert_file: Path):
    """Migrate alert_history.json to AlertHistory table."""
    try:
        with open(alert_file, "r") as f:
            alert_data = json.load(f)

        with AlertHistoryRepository(session) as alert_repo:
            total_alerts = 0
            for stock_symbol, dates in alert_data.items():
                for date in dates:
                    alert_repo.add_alert(stock_symbol, date)
                    total_alerts += 1
                print(f"Migrated {len(dates)} alerts for {stock_symbol}")

        print(f"Migrated {total_alerts} total alerts")

    except Exception as e:
        print(f"Error migrating alert history: {e}")


def backup_json_files():
    """Create backup copies of JSON files before migration."""
    resources_dir = Path(__file__).parent.parent.parent.parent / "resources"

    files_to_backup = ["tracker_list.json", "alert_history.json"]

    for filename in files_to_backup:
        original = resources_dir / filename
        if original.exists():
            backup = resources_dir / f"{filename}.backup"
            backup.write_text(original.read_text())
            print(f"Backed up {filename} to {backup}")


def verify_migration():
    """Verify that the migration was successful."""
    print("Verifying migration...")

    with get_session_sync() as session:
        # Check stocks
        with TrackedStockRepository(session) as stock_repo:
            stocks = stock_repo.get_all_active_stocks()
            print(f"Found {len(stocks)} tracked stocks in database")
            for stock in stocks:
                print(f"  - {stock.symbol}")

        # Check alerts
        with AlertHistoryRepository(session) as alert_repo:
            for stock in stocks:
                alerts = alert_repo.get_alerts_for_stock(str(stock.symbol))
                print(f"  {stock.symbol}: {len(alerts)} alerts")


if __name__ == "__main__":
    # Run migration
    backup_json_files()
    migrate_json_to_database()
    verify_migration()
