"""AI agent handlers for message processing and stock research."""

from agents import Agent, Runner, WebSearchTool

from ..comm.chat_history import chat_history_manager
from ..comm.telegram import send_telegram_message, telegram_bot
from ..config.logging import get_logger
from ..core.agent_tools import (
    add_politician_to_tracker,
    add_stock_to_tracker,
    get_politician_activity_info,
    get_stock_price_info,
    get_tracked_politicians_list,
    get_tracked_stocks_list,
    remove_politician_from_tracker,
    remove_stock_from_tracker,
)
from .prompts import (
    get_conversation_summarizer_config,
    get_error_message,
    get_message_handler_config,
    get_research_pipeline_template,
    get_stock_research_config,
    get_summarizer_config,
)

logger = get_logger(__name__)

# Load agent configurations from external prompts
_message_handler_config = get_message_handler_config()
_stock_research_config = get_stock_research_config()
_summarizer_config = get_summarizer_config()
_conversation_summarizer_config = get_conversation_summarizer_config()

# Message handling agent for processing user commands
message_handler_agent = Agent(
    name=_message_handler_config["name"],
    instructions=_message_handler_config["instructions"],
    tools=[
        add_stock_to_tracker,
        add_politician_to_tracker,
        get_stock_price_info,
        get_tracked_stocks_list,
        get_tracked_politicians_list,
        get_politician_activity_info,
        remove_stock_from_tracker,
        remove_politician_from_tracker,
    ],
    model=_message_handler_config["model"],
)


# Stock research agent for analyzing price movements
stock_research_agent = Agent(
    name=_stock_research_config["name"],
    instructions=_stock_research_config["instructions"],
    tools=[get_stock_price_info, WebSearchTool()],
    model=_stock_research_config["model"],
)


# Summarizer agent for creating concise alerts
summarizer_agent = Agent(
    name=_summarizer_config["name"],
    instructions=_summarizer_config["instructions"],
    model=_summarizer_config["model"],
)


# Conversation summarizer agent for analyzing chat history
conversation_summarizer_agent = Agent(
    name=_conversation_summarizer_config["name"],
    instructions=_conversation_summarizer_config["instructions"],
    model=_conversation_summarizer_config["model"],
)


async def handle_incoming_message(message: str, chat_id: str | None = None) -> str:
    """
    Handle incoming user messages and return appropriate responses.

    Args:
        message: User message text
        chat_id: Telegram chat ID to fetch conversation history

    Returns:
        Response text for the user
    """
    logger.info("Processing message:")  # , message)

    try:
        # Fetch conversation history if chat_id is provided
        conversation_context = ""
        if chat_id:
            # Get conversation summary from local storage
            conversation_summary = chat_history_manager.get_conversation_summary(
                chat_id, limit=5
            )
            if (
                conversation_summary
                and conversation_summary != "No previous conversation history."
            ):
                # Summarize the conversation history for context using AI
                history_response = await Runner.run(
                    conversation_summarizer_agent,
                    f"Recent conversation history:\n{conversation_summary}",
                )
                conversation_context = (
                    f"\n\nConversation Context: {history_response.final_output}"
                )

        # Include conversation context with the current message
        full_message = message + conversation_context

        response = await Runner.run(message_handler_agent, full_message)
        return response.final_output
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return get_error_message("general_error")


async def run_research_pipeline(
    stock_symbol: str, current_price: float, previous_close: float
) -> str:
    """
    Run the research pipeline for a stock that has had significant price movement.

    Args:
        stock_symbol: Stock ticker symbol
        current_price: Current stock price
        previous_close: Previous closing price

    Returns:
        Final research summary
    """
    logger.info(f"Running research pipeline for {stock_symbol}")

    try:
        # Run stock research
        response = await Runner.run(stock_research_agent, stock_symbol)
        logger.info(f"Research pipeline response: {response}")

        # Calculate percentage change
        change_percent = (current_price / previous_close - 1) * 100

        # Create message for summarizer using template
        template = get_research_pipeline_template()
        message_to_summarizer = template.format(
            stock_symbol=stock_symbol,
            change_percent=change_percent,
            research_output=response.final_output,
        )

        # Generate summary
        summarizer_response = await Runner.run(summarizer_agent, message_to_summarizer)
        logger.info(f"Summarizer response: {summarizer_response}")

        final_output = summarizer_response.final_output

        # Send notification via Telegram
        await send_telegram_message(final_output)

        return final_output

    except Exception as e:
        logger.error(f"Error in research pipeline: {e}")
        error_template = get_error_message("research_failed")
        error_message = error_template.format(stock_symbol=stock_symbol)
        await send_telegram_message(error_message)
        return error_message
