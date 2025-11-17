"""Tests for agent handlers."""

# Import modules to test
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.append("src")
from sentinel.agents.handlers import (
    conversation_summarizer_agent,
    handle_incoming_message,
    message_handler_agent,
    politician_research_agent,
    run_politician_research_pipeline,
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
        assert (
            len(message_handler_agent.tools) == 8
        )  # Should have 8 tools (stock + politician tools)

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

    def test_politician_research_agent_created(self):
        """Test politician research agent is created correctly."""
        assert politician_research_agent.name == "Congressional Trading Research Agent"
        assert politician_research_agent.model == "gpt-4.1"
        assert len(politician_research_agent.tools) == 2  # Should have 2 tools

    def test_conversation_summarizer_agent_created(self):
        """Test conversation summarizer agent is created correctly."""
        assert conversation_summarizer_agent.name == "Conversation History Summarizer"
        assert conversation_summarizer_agent.model == "gpt-4o-mini"
        assert len(conversation_summarizer_agent.tools) == 0  # Summarizer has no tools


class TestHandleIncomingMessage:
    """Test the handle_incoming_message function."""

    @pytest.mark.asyncio
    async def test_successful_message_handling(self):
        """Test successful message handling."""
        mock_response = Mock()
        mock_response.final_output = "Successfully processed message"

        with patch(
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = mock_response

            result = await handle_incoming_message("test message")

            assert result == "Successfully processed message"
            mock_runner.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in message processing."""
        with patch(
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch("sentinel.agents.handlers.get_error_message") as mock_error:
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
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            mock_runner.return_value = mock_response

            await handle_incoming_message("test message")

            # Check that the message was logged
            captured = capfd.readouterr()
            assert "Processing message:" in captured.out


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
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ) as mock_telegram:
                with patch(
                    "sentinel.agents.handlers.get_research_pipeline_template"
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
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ):
                with patch(
                    "sentinel.agents.handlers.get_research_pipeline_template"
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
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ) as mock_telegram:
                with patch("sentinel.agents.handlers.get_error_message") as mock_error:
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
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ):
                with patch("sentinel.agents.handlers.get_research_pipeline_template"):
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
        "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
    ) as mock_runner:
        with patch(
            "sentinel.agents.handlers.send_telegram_message",
            new_callable=AsyncMock,
        ):
            with patch(
                "sentinel.agents.handlers.get_research_pipeline_template"
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


class TestConversationHistory:
    """Test conversation history functionality."""

    @pytest.mark.asyncio
    async def test_handle_message_with_conversation_history(self):
        """Test that conversation history is fetched and used when chat_id is provided."""
        # Mock the conversation summary from chat history manager
        with patch(
            "sentinel.agents.handlers.chat_history_manager"
        ) as mock_history_manager:
            mock_history_manager.get_conversation_summary.return_value = (
                "User: What's the price of AAPL?\n"
                "Bot: AAPL is currently trading at $150.00"
            )

            # Mock the Runner.run method for both agents
            with patch("sentinel.agents.handlers.Runner") as mock_runner:
                # Mock response for conversation summarizer
                mock_summarizer_response = AsyncMock()
                mock_summarizer_response.final_output = (
                    "User previously asked about AAPL stock price"
                )

                # Mock response for message handler
                mock_handler_response = AsyncMock()
                mock_handler_response.final_output = (
                    "Based on our conversation, I can help track AAPL."
                )

                # Configure Runner.run to return different responses
                def mock_run(agent, message):
                    if "Conversation History Summarizer" in str(agent.name):
                        return mock_summarizer_response
                    else:
                        return mock_handler_response

                mock_runner.run = AsyncMock(side_effect=mock_run)

                # Test the function with a chat_id
                result = await handle_incoming_message(
                    "Track AAPL stock", chat_id="test_chat_123"
                )

                # Verify that get_conversation_summary was called with the correct chat_id
                mock_history_manager.get_conversation_summary.assert_called_once_with(
                    "test_chat_123", limit=5
                )

                # Verify that Runner.run was called twice
                assert mock_runner.run.call_count == 2

                # Check the final result
                assert result == "Based on our conversation, I can help track AAPL."

                # Verify the conversation context was included in the message handler call
                handler_call_args = mock_runner.run.call_args_list[1][0]
                full_message = handler_call_args[1]
                assert "Track AAPL stock" in full_message
                assert "Conversation Context:" in full_message
                assert "User previously asked about AAPL stock price" in full_message

    @pytest.mark.asyncio
    async def test_handle_message_without_chat_id(self):
        """Test that function works normally when no chat_id is provided."""
        with patch("sentinel.agents.handlers.Runner") as mock_runner:
            mock_response = AsyncMock()
            mock_response.final_output = "I can help you with stock information."
            mock_runner.run = AsyncMock(return_value=mock_response)

            result = await handle_incoming_message("Get stock info")

            # Should only call Runner.run once (no conversation summarizer)
            mock_runner.run.assert_called_once()

            # Message should not contain conversation context
            call_args = mock_runner.run.call_args[0]
            message = call_args[1]

            assert message == "Get stock info"  # No additional context
            assert "Conversation Context:" not in message
            assert result == "I can help you with stock information."

    @pytest.mark.asyncio
    async def test_handle_message_with_empty_chat_history(self):
        """Test handling when chat history is empty."""
        with patch(
            "sentinel.agents.handlers.chat_history_manager"
        ) as mock_history_manager:
            # Return the default "no history" message
            mock_history_manager.get_conversation_summary.return_value = (
                "No previous conversation history."
            )

            with patch("sentinel.agents.handlers.Runner") as mock_runner:
                mock_response = AsyncMock()
                mock_response.final_output = "How can I help you?"
                mock_runner.run = AsyncMock(return_value=mock_response)

                result = await handle_incoming_message("Hello", chat_id="test_chat")

                # Should only call message handler (no conversation summarizer for empty history)
                mock_runner.run.assert_called_once()

                # Message should be unchanged
                call_args = mock_runner.run.call_args[0]
                message = call_args[1]
                assert message == "Hello"
                assert "Conversation Context:" not in message

    @pytest.mark.asyncio
    async def test_handle_message_with_chat_history_error(self):
        """Test handling when chat history fetch fails."""
        with patch(
            "sentinel.agents.handlers.chat_history_manager"
        ) as mock_history_manager:
            # Simulate error in get_conversation_summary
            mock_history_manager.get_conversation_summary.side_effect = Exception(
                "Database Error"
            )

            with patch("sentinel.agents.handlers.get_error_message") as mock_error:
                mock_error.return_value = (
                    "Sorry, there was an error processing your request."
                )

                result = await handle_incoming_message(
                    "Track NVDA", chat_id="test_chat"
                )

                # Should call error handler
                mock_error.assert_called_once_with("general_error")
                assert result == "Sorry, there was an error processing your request."

    @pytest.mark.asyncio
    async def test_conversation_summarizer_agent_functionality(self):
        """Test the conversation summarizer agent directly."""
        mock_conversation_summary = (
            "User: What's TSLA doing today?\n"
            "Bot: TSLA is currently trading at $220.50\n"
            "User: Add MSFT to my watchlist"
        )

        with patch(
            "sentinel.agents.handlers.chat_history_manager"
        ) as mock_history_manager:
            mock_history_manager.get_conversation_summary.return_value = (
                mock_conversation_summary
            )

            with patch("sentinel.agents.handlers.Runner") as mock_runner:
                mock_summarizer_response = AsyncMock()
                mock_summarizer_response.final_output = (
                    "User asked about TSLA and wants to track MSFT"
                )

                mock_handler_response = AsyncMock()
                mock_handler_response.final_output = "I'll help you track these stocks"

                def mock_run(agent, message):
                    if "Conversation History Summarizer" in str(agent.name):
                        # Verify conversation summary is passed correctly
                        assert "Recent conversation history:" in message
                        assert "What's TSLA doing today?" in message
                        assert "Add MSFT to my watchlist" in message
                        return mock_summarizer_response
                    else:
                        return mock_handler_response

                mock_runner.run = AsyncMock(side_effect=mock_run)

                result = await handle_incoming_message(
                    "Show my portfolio", chat_id="test_chat"
                )

                # Verify that get_conversation_summary was called
                mock_history_manager.get_conversation_summary.assert_called_once_with(
                    "test_chat", limit=5
                )

                # Check that Runner.run was called twice (summarizer + handler)
                assert mock_runner.run.call_count == 2

                # Check the final result
                assert result == "I'll help you track these stocks"

                # Verify the conversation context was included in the message handler call
                handler_call_args = mock_runner.run.call_args_list[1][0]
                full_message = handler_call_args[1]
                assert "Show my portfolio" in full_message
                assert "Conversation Context:" in full_message
                assert "User asked about TSLA and wants to track MSFT" in full_message

    @pytest.mark.asyncio
    async def test_message_handler_receives_enhanced_context(self):
        """Test that the message handler receives the enhanced message with context."""
        mock_chat_history = [
            {
                "message_id": 1,
                "text": "I'm interested in tech stocks",
                "from": {"first_name": "Bob"},
                "date": 1640000000,
            }
        ]

        with patch(
            "sentinel.agents.handlers.chat_history_manager"
        ) as mock_history_manager:
            mock_history_manager.get_conversation_summary.return_value = (
                "User: I'm interested in tech stocks (Bob)\n"
                "Bot: I can help you find good tech stocks to invest in"
            )

            with patch("sentinel.agents.handlers.Runner") as mock_runner:
                # Mock conversation summarizer response
                mock_summarizer_response = AsyncMock()
                mock_summarizer_response.final_output = (
                    "User is interested in technology stocks"
                )

                # Mock message handler response
                mock_handler_response = AsyncMock()
                mock_handler_response.final_output = (
                    "Here are some tech stocks to consider"
                )

                def mock_run(agent, message):
                    if "Conversation History Summarizer" in str(agent.name):
                        return mock_summarizer_response
                    else:
                        # Verify the enhanced message format
                        assert "What tech stocks do you recommend?" in message
                        assert (
                            "\n\nConversation Context: User is interested in technology stocks"
                            in message
                        )
                        return mock_handler_response

                mock_runner.run = AsyncMock(side_effect=mock_run)

                result = await handle_incoming_message(
                    "What tech stocks do you recommend?", chat_id="test_chat"
                )

                assert result == "Here are some tech stocks to consider"
                assert mock_runner.run.call_count == 2

    @pytest.mark.asyncio
    async def test_conversation_history_with_multiple_users(self):
        """Test conversation history handling with multiple users in chat."""
        mock_conversation_summary = (
            "User: AAPL earnings today (Alice)\n"
            "Bot: AAPL will report earnings after market close\n"
            "User: Good luck! (Bob)"
        )

        with patch(
            "sentinel.agents.handlers.chat_history_manager"
        ) as mock_history_manager:
            mock_history_manager.get_conversation_summary.return_value = (
                mock_conversation_summary
            )

            with patch("sentinel.agents.handlers.Runner") as mock_runner:
                mock_summarizer_response = AsyncMock()
                mock_summarizer_response.final_output = "Discussion about AAPL earnings"

                mock_handler_response = AsyncMock()
                mock_handler_response.final_output = "AAPL earnings were strong"

                def mock_run(agent, message):
                    if "Conversation History Summarizer" in str(agent.name):
                        # Verify both users' messages are included in the history
                        assert "AAPL earnings today" in message
                        assert "Good luck!" in message
                        assert "Alice" in message
                        assert "Bob" in message
                        return mock_summarizer_response
                    else:
                        return mock_handler_response

                mock_runner.run = AsyncMock(side_effect=mock_run)

                result = await handle_incoming_message(
                    "How did AAPL do?", chat_id="group_chat"
                )

                # Should call both summarizer and handler
                assert mock_runner.run.call_count == 2
                assert result == "AAPL earnings were strong"


class TestPoliticianResearchPipeline:
    """Test the run_politician_research_pipeline function."""

    @pytest.mark.asyncio
    async def test_successful_politician_research_pipeline(self):
        """Test successful politician research pipeline execution."""
        mock_research_response = Mock()
        mock_research_response.final_output = (
            "Nancy Pelosi's AAPL trade appears motivated by earnings optimism"
        )

        with patch(
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ) as mock_telegram:
                with patch(
                    "sentinel.agents.handlers.get_politician_research_template"
                ) as mock_template:
                    # Setup mocks
                    mock_runner.return_value = mock_research_response
                    mock_template.return_value = "{politician_name}: {research_output}"

                    result = await run_politician_research_pipeline("Nancy Pelosi")

                    assert (
                        result
                        == "Nancy Pelosi: Nancy Pelosi's AAPL trade appears motivated by earnings optimism"
                    )
                    assert (
                        mock_runner.call_count == 1
                    )  # Only the research agent, not summarizer
                    mock_telegram.assert_called_once_with(
                        "Nancy Pelosi: Nancy Pelosi's AAPL trade appears motivated by earnings optimism"
                    )

    @pytest.mark.asyncio
    async def test_politician_research_pipeline_error_handling(self):
        """Test error handling in politician research pipeline."""
        with patch(
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ) as mock_telegram:
                with patch("sentinel.agents.handlers.get_error_message") as mock_error:
                    # Setup error scenario
                    mock_runner.side_effect = Exception("Research failed")
                    mock_error.return_value = "{politician_name} trading activity detected, but analysis failed."

                    result = await run_politician_research_pipeline("Nancy Pelosi")

                    expected_error = (
                        "Nancy Pelosi trading activity detected, but analysis failed."
                    )
                    assert result == expected_error
                    mock_telegram.assert_called_once_with(expected_error)
                    mock_error.assert_called_once_with("politician_research_failed")

    @pytest.mark.asyncio
    async def test_politician_research_pipeline_logging(self, capfd):
        """Test that politician research pipeline logs correctly."""
        mock_response = Mock()
        mock_response.final_output = "Research completed"

        with patch(
            "sentinel.agents.handlers.Runner.run", new_callable=AsyncMock
        ) as mock_runner:
            with patch(
                "sentinel.agents.handlers.send_telegram_message",
                new_callable=AsyncMock,
            ):
                with patch("sentinel.agents.handlers.get_politician_research_template"):
                    mock_runner.return_value = mock_response

                    await run_politician_research_pipeline("Nancy Pelosi")

                    captured = capfd.readouterr()
                    assert (
                        "Running politician research pipeline for Nancy Pelosi"
                        in captured.out
                    )
