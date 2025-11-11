"""Tests for agent handlers."""

# Import modules to test
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append("src")
from stock_tracker.agents.handlers import (
    handle_incoming_message,
    message_handler_agent,
    run_research_pipeline,
    stock_research_agent,
    summarizer_agent,
)


class TestAgentCreation:
    """Test that agents are created with correct configurations."""

    def test_message_handler_agent_created(self):
        """Test message handler agent is created correctly."""
        assert message_handler_agent.name == "Message Handler Agent"
        assert message_handler_agent.model == "gpt-4o-mini"
        assert len(message_handler_agent.tools) == 4  # Should have 4 tools

    def test_stock_research_agent_created(self):
        """Test stock research agent is created correctly."""
        assert stock_research_agent.name == "Stock Research Agent"
        assert stock_research_agent.model == "gpt-4.1"
        assert len(stock_research_agent.tools) == 2  # Should have 2 tools

    def test_summarizer_agent_created(self):
        """Test summarizer agent is created correctly."""
        assert summarizer_agent.name == "Summarizer Agent"
        assert summarizer_agent.model == "gpt-4o-mini"
        assert len(summarizer_agent.tools) == 0  # Summarizer has no tools


class TestHandleIncomingMessage:
    """Test the handle_incoming_message function."""

    @pytest.mark.asyncio
    async def test_successful_message_handling(self):
        """Test successful message handling."""
        mock_response = Mock()
        mock_response.final_output = "Successfully processed message"

        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = mock_response

            result = await handle_incoming_message("test message")

            assert result == "Successfully processed message"
            mock_runner.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in message processing."""
        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch("stock_tracker.agents.handlers.get_error_message") as mock_error:
                mock_runner.side_effect = Exception("Test error")
                mock_error.return_value = "Error occurred"

                result = await handle_incoming_message("test message")

                assert result == "Error occurred"
                mock_error.assert_called_once_with("general_error")

    @pytest.mark.asyncio
    async def test_message_logging(self, capfd):
        """Test that messages are logged correctly."""
        mock_response = Mock()
        mock_response.final_output = "Test response"

        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = mock_response

            await handle_incoming_message("test message")

            # Check that the message was logged
            captured = capfd.readouterr()
            assert "Processing message: test message" in captured.out


class TestRunResearchPipeline:
    """Test the run_research_pipeline function."""

    @pytest.mark.asyncio
    async def test_successful_research_pipeline(self):
        """Test successful research pipeline execution."""
        mock_research_response = Mock()
        mock_research_response.final_output = "Stock went up due to earnings"

        mock_summarizer_response = Mock()
        mock_summarizer_response.final_output = "AAPL UP 2.50%: earnings beat"

        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "stock_tracker.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ) as mock_telegram:
                with patch(
                    "stock_tracker.agents.handlers.get_research_pipeline_template"
                ) as mock_template:
                    # Setup mocks
                    mock_runner.side_effect = [
                        mock_research_response,
                        mock_summarizer_response,
                    ]
                    mock_template.return_value = (
                        "{stock_symbol} {change_percent:+.2f}%: {research_output}"
                    )

                    result = await run_research_pipeline("AAPL", 150.0, 147.0)

                    assert result == "AAPL UP 2.50%: earnings beat"
                    assert mock_runner.call_count == 2
                    mock_telegram.assert_called_once_with(
                        "AAPL UP 2.50%: earnings beat"
                    )

    @pytest.mark.asyncio
    async def test_percentage_change_calculation(self):
        """Test that percentage change is calculated correctly."""
        mock_research_response = Mock()
        mock_research_response.final_output = "Test research"

        mock_summarizer_response = Mock()
        mock_summarizer_response.final_output = "Test summary"

        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "stock_tracker.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ):
                with patch(
                    "stock_tracker.agents.handlers.get_research_pipeline_template"
                ) as mock_template:
                    mock_runner.side_effect = [
                        mock_research_response,
                        mock_summarizer_response,
                    ]

                    # Mock template that captures the change_percent
                    def capture_format(**kwargs):
                        assert (
                            abs(kwargs["change_percent"] - 1.35) < 0.01
                        )  # 150/148 - 1 = 0.0135 = 1.35%
                        return f"{kwargs['stock_symbol']} {kwargs['change_percent']:+.2f}%: {kwargs['research_output']}"

                    mock_template.return_value.format = capture_format

                    await run_research_pipeline("AAPL", 150.0, 148.0)

    @pytest.mark.asyncio
    async def test_research_pipeline_error_handling(self):
        """Test error handling in research pipeline."""
        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "stock_tracker.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ) as mock_telegram:
                with patch(
                    "stock_tracker.agents.handlers.get_error_message"
                ) as mock_error:
                    # Setup error scenario
                    mock_runner.side_effect = Exception("Research failed")
                    mock_error.return_value = (
                        "{stock_symbol} price movement detected, but analysis failed."
                    )

                    result = await run_research_pipeline("AAPL", 150.0, 147.0)

                    expected_error = (
                        "AAPL price movement detected, but analysis failed."
                    )
                    assert result == expected_error
                    mock_telegram.assert_called_once_with(expected_error)
                    mock_error.assert_called_once_with("research_failed")

    @pytest.mark.asyncio
    async def test_research_pipeline_logging(self, capfd):
        """Test that research pipeline logs correctly."""
        mock_response = Mock()
        mock_response.final_output = "Test"

        with patch(
            "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "stock_tracker.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ):
                with patch(
                    "stock_tracker.agents.handlers.get_research_pipeline_template"
                ):
                    mock_runner.return_value = mock_response

                    await run_research_pipeline("AAPL", 150.0, 147.0)

                    captured = capfd.readouterr()
                    assert "Running research pipeline for AAPL" in captured.out


@pytest.mark.parametrize(
    "current_price,previous_close,expected_change",
    [
        (150.0, 147.0, 2.04),  # Positive change
        (147.0, 150.0, -2.0),  # Negative change
        (100.0, 100.0, 0.0),  # No change
        (110.0, 100.0, 10.0),  # 10% increase
    ],
)
@pytest.mark.asyncio
async def test_percentage_calculations(current_price, previous_close, expected_change):
    """Test percentage change calculations with various inputs."""
    mock_research_response = Mock()
    mock_research_response.final_output = "Test"

    mock_summarizer_response = Mock()
    mock_summarizer_response.final_output = "Test"

    with patch(
        "stock_tracker.agents.handlers.Runner.run", new_callable=AsyncMock
    ) as mock_runner:
        with patch(
            "stock_tracker.agents.handlers.send_telegram_message",
            new_callable=AsyncMock,
        ):
            with patch(
                "stock_tracker.agents.handlers.get_research_pipeline_template"
            ) as mock_template:
                mock_runner.side_effect = [
                    mock_research_response,
                    mock_summarizer_response,
                ]

                def capture_format(**kwargs):
                    # Check that percentage is calculated correctly
                    actual_change = kwargs["change_percent"]
                    assert abs(actual_change - expected_change) < 0.1
                    return "formatted message"

                mock_template.return_value.format = capture_format

                await run_research_pipeline("TEST", current_price, previous_close)
