"""FastAPI application and webhook endpoints."""

import os
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..agents.handlers import handle_incoming_message
from ..comm.chat_history import chat_history_manager
from ..comm.telegram import telegram_bot
from ..config.logging import get_logger
from ..config.settings import get_settings

# Get settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Security scheme for Bearer token authentication
security = HTTPBearer()


def verify_auth_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    Verify the authentication token.

    Args:
        credentials: The HTTP authorization credentials

    Returns:
        The token if valid

    Raises:
        HTTPException: If token is invalid
    """
    expected_token = settings.endpoint_auth_token
    if not expected_token:
        logger.error("Endpoint auth token not configured")
        raise HTTPException(
            detail="ENDPOINT_AUTH_TOKEN not configured", status_code=500
        )

    if credentials.credentials != expected_token:
        logger.warning(
            "Invalid authentication attempt",
            provided_token_length=len(credentials.credentials),
        )
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    logger.debug("Authentication successful")
    return credentials.credentials


def verify_telegram_webhook_auth(request: Request) -> bool:
    """
    Verify Telegram webhook authentication using the X-Telegram-Bot-Api-Secret-Token header.

    Args:
        request: The incoming request

    Returns:
        True if authenticated, False otherwise
    """
    expected_token = settings.telegram_auth_token
    if not expected_token:
        logger.error("Telegram auth token not configured")
        return False

    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret_token:
        logger.warning("Missing Telegram webhook secret header")
        return False

    is_valid = secret_token == expected_token
    if not is_valid:
        logger.warning("Invalid Telegram webhook authentication")
    else:
        logger.debug("Telegram webhook authentication successful")

    return is_valid


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Sentinel",
        description="AI-powered stock monitoring with Telegram notifications",
        version="1.0.0",
    )

    @app.get("/")
    async def root(token: str = Depends(verify_auth_token)):
        """Health check endpoint."""
        logger.info("Health check endpoint accessed")
        return {"message": "Sentinel is running"}

    @app.get("/health")
    async def health_check(token: str = Depends(verify_auth_token)):
        """Health check endpoint."""
        logger.info("Health status endpoint accessed")
        return {"status": "healthy"}

    @app.post("/webhook/tg-nqlftdvdqi")
    async def telegram_webhook(request: Request):
        """
        Handle incoming Telegram webhook updates.

        This endpoint receives updates from Telegram when users send messages.
        Uses X-Telegram-Bot-Api-Secret-Token header for authentication.
        """
        # Verify Telegram webhook authentication, return 404 if invalid
        if not verify_telegram_webhook_auth(request):
            raise HTTPException(status_code=404, detail="Not Found")

        try:
            update: Dict[str, Any] = await request.json()

            # Extract message information
            text, chat_id, user_id = telegram_bot.extract_message_info(update)

            if not text or not chat_id:
                return JSONResponse(content={"status": "ignored"}, status_code=200)

            # Check if message is from authorized user
            if chat_id != settings.telegram_chat_id:
                logger.warning(
                    "Unauthorized message attempt",
                    received_chat_id=chat_id,
                    authorized_chat_id=settings.telegram_chat_id,
                )
                await telegram_bot.send_message(
                    "Sorry, you are not authorized to use this bot.", chat_id=chat_id
                )
                return JSONResponse(content={"status": "unauthorized"}, status_code=200)

            print(f"Received message from {chat_id}: {text}")

            # Store the incoming user message in chat history
            user_info = update.get("message", {}).get("from", {})
            username = user_info.get("first_name", "User")
            message_id = update.get("message", {}).get("message_id")

            chat_history_manager.store_user_message(
                chat_id=chat_id,
                message_text=text,
                user_id=user_id,
                username=username,
                message_id=str(message_id) if message_id else None,
            )

            # Process the message
            response_text = await handle_incoming_message(text, chat_id=chat_id)

            # Send response back to user
            await telegram_bot.send_message(response_text, chat_id=chat_id)

            return JSONResponse(content={"status": "ok"}, status_code=200)

        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JSONResponse(
                content={"error": "Internal server error"}, status_code=500
            )

    @app.post("/webhook/set")
    async def set_webhook(webhook_url: str, token: str = Depends(verify_auth_token)):
        """
        Set the Telegram webhook URL.

        Args:
            webhook_url: The URL where Telegram should send updates
            token: Authentication token (provided via Authorization header)
        """
        try:
            # Use the same token for webhook secret authentication
            auth_token = os.getenv("TELEGRAM_AUTH_TOKEN")
            success = await telegram_bot.set_webhook(
                webhook_url, secret_token=auth_token
            )
            if success:
                return {
                    "status": "webhook set successfully",
                    "url": webhook_url,
                    "secret_token_configured": bool(auth_token),
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to set webhook")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error setting webhook: {e}")

    @app.get("/webhook/info")
    async def get_webhook_info(token: str = Depends(verify_auth_token)):
        """
        Get current webhook information.

        Args:
            token: Authentication token (provided via Authorization header)
        """
        try:
            info = await telegram_bot.get_webhook_info()
            return info
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error getting webhook info: {e}"
            )

    @app.delete("/webhook")
    async def delete_webhook(token: str = Depends(verify_auth_token)):
        """
        Delete the current webhook.

        Args:
            token: Authentication token (provided via Authorization header)
        """
        try:
            success = await telegram_bot.delete_webhook()
            if success:
                return {"status": "webhook deleted successfully"}
            else:
                raise HTTPException(status_code=400, detail="Failed to delete webhook")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting webhook: {e}")

    return app


# Create the app instance
app = create_app()
