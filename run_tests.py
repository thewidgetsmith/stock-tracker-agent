#!/usr/bin/env python3
"""
Test runner script with common testing commands.

This script provides shortcuts for running different types of tests.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print the description."""
    print(f"\n🧪 {description}")
    print("=" * 50)
    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <command>")
        print("\nAvailable commands:")
        print("  all        - Run all tests with coverage")
        print("  unit       - Run unit tests only")
        print("  api        - Run API tests only")
        print("  agents     - Run agent tests only")
        print("  core       - Run core functionality tests")
        print("  fast       - Run tests without coverage")
        print("  coverage   - Generate coverage report")
        print("  clean      - Clean test artifacts")
        return

    command = sys.argv[1].lower()

    if command == "all":
        success = run_command(
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=src",
                "--cov-report=html",
                "-v",
            ],
            "Running all tests with coverage",
        )
    elif command == "unit":
        success = run_command(
            ["python", "-m", "pytest", "tests/", "-m", "not integration", "-v"],
            "Running unit tests only",
        )
    elif command == "api":
        success = run_command(
            ["python", "-m", "pytest", "tests/test_api/", "-v"], "Running API tests"
        )
    elif command == "agents":
        success = run_command(
            ["python", "-m", "pytest", "tests/test_agents/", "-v"],
            "Running agent tests",
        )
    elif command == "core":
        success = run_command(
            ["python", "-m", "pytest", "tests/test_core/", "-v"],
            "Running core functionality tests",
        )
    elif command == "fast":
        success = run_command(
            ["python", "-m", "pytest", "tests/", "--no-cov", "-v"],
            "Running tests without coverage (fast)",
        )
    elif command == "coverage":
        success = run_command(
            [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=src",
                "--cov-report=html",
                "--cov-report=term",
            ],
            "Generating coverage report",
        )
        if success:
            print("\n📊 Coverage report generated!")
            print("   - Terminal report shown above")
            print("   - HTML report: htmlcov/index.html")
    elif command == "clean":
        success = True
        artifacts = [
            ".coverage",
            "htmlcov/",
            ".pytest_cache/",
            "**/__pycache__/",
            "**/*.pyc",
        ]
        print("\n🧹 Cleaning test artifacts...")
        for pattern in artifacts:
            subprocess.run(
                ["find", ".", "-name", pattern.replace("**/", ""), "-delete"],
                capture_output=True,
            )
        print("✅ Test artifacts cleaned!")
    else:
        print(f"❌ Unknown command: {command}")
        return

    if command != "clean":
        if success:
            print(f"\n✅ {command.title()} tests completed successfully!")
        else:
            print(f"\n❌ {command.title()} tests failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
