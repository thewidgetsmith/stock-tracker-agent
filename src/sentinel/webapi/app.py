"""FastAPI application with enhanced API architecture and service layer integration."""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..agents.handlers import handle_incoming_message
from ..comm.chat_history import chat_history_manager
from ..comm.telegram import telegram_bot
from ..config.logging import get_logger
from ..config.settings import get_settings
from ..events import get_event_bus
from .exceptions import NotFoundError, ValidationException, setup_exception_handlers
from .health import router as health_router
from .models.responses import ErrorResponse, MessageResponse, StatusResponse
from .routers import notifications_router, stocks_router

# Get settings and logger
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with enhanced initialization."""
    # Startup
    logger.info("Starting Sentinel Stock Tracker API with service layer")

    # Initialize event system
    try:
        event_bus = get_event_bus()
        logger.info("Event system initialized", event_bus_name=event_bus.name)
    except Exception as e:
        logger.error("Failed to initialize event system", error=str(e), exc_info=True)
        raise RuntimeError(f"Event system initialization failed: {str(e)}")

    logger.info("Sentinel Stock Tracker API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Sentinel Stock Tracker API")

    # Cleanup event system
    try:
        event_bus = get_event_bus()
        # Could add event bus shutdown logic here if needed
        logger.info("Event system shutdown completed")
    except Exception as e:
        logger.error("Error during event system shutdown", error=str(e), exc_info=True)

    logger.info("Sentinel Stock Tracker API shutdown completed")


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
    expected_token = settings.fastapi_auth_token
    if not expected_token:
        logger.error("Fastapi auth token not configured")
        raise HTTPException(detail="FASTAPI_AUTH_TOKEN not configured", status_code=500)

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


async def add_request_id_middleware(request: Request, call_next):
    """Add unique request ID to each request for tracking."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Log request start
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None,
    )

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    # Log request completion
    logger.info(
        "Request completed",
        request_id=request_id,
        status_code=response.status_code,
        method=request.method,
        path=request.url.path,
    )

    return response


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with enhanced architecture."""
    app = FastAPI(
        title="Sentinel Stock Tracker API",
        description="""
        Advanced stock tracking and alerting system with event-driven architecture.

        ## Features

        * **Stock Tracking**: Monitor stock prices and detect significant movements
        * **Portfolio Management**: Track multiple stocks in your portfolio
        * **Smart Alerts**: Configurable alerts with multiple notification channels
        * **Real-time Events**: Event-driven architecture for real-time processing
        * **Multi-channel Notifications**: Telegram, Email, and Webhook support
        * **Comprehensive Analytics**: Historical data and performance tracking
        * **Telegram Integration**: Chat-based interaction with the system

        ## Architecture

        Built with modern architectural patterns:
        - Service Layer Pattern for business logic encapsulation
        - Event-Driven Architecture for decoupled communication
        - Repository Pattern for data access abstraction
        - Comprehensive error handling and logging
        - Request tracking and middleware
        """,
        version="2.0.0",
        contact={
            "name": "Sentry Agents Development Team",
            "email": "dev@sentryagents.com",
        },
        license_info={
            "name": "MIT",
        },
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add middleware for request tracking
    app.middleware("http")(add_request_id_middleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include health check router
    app.include_router(health_router, prefix="/api/v1", tags=["Health & Status"])

    # Include new enhanced routers
    app.include_router(
        stocks_router, prefix="/api/v1", tags=["Stock Tracking & Analysis"]
    )

    app.include_router(
        notifications_router,
        prefix="/api/v1",
        tags=["Notifications & System Management"],
    )

    @app.get(
        "/",
        response_model=MessageResponse,
        summary="API Root Endpoint",
        description="Basic API information with navigation links",
    )
    async def root(
        request: Request, token: str = Depends(verify_auth_token)
    ) -> MessageResponse:
        """Enhanced API root endpoint with navigation."""
        request_id = request.state.request_id

        return MessageResponse.create(
            message="Sentinel Stock Tracker API - Enhanced with Service Layer Architecture",
            request_id=request_id,
        )

    @app.get(
        "/api/v1/status",
        response_model=StatusResponse,
        summary="Enhanced API Status",
        description="Comprehensive API status with service layer information",
    )
    async def api_status(
        request: Request, token: str = Depends(verify_auth_token)
    ) -> StatusResponse:
        """Enhanced API status endpoint with service layer details."""
        request_id = request.state.request_id

        # Check event bus status
        try:
            event_bus = get_event_bus()
            event_stats = event_bus.get_statistics()
            event_status = "operational"
        except Exception as e:
            event_stats = {"error": str(e)}
            event_status = "error"

        status_data = {
            "api_version": "2.0.0",
            "status": "operational",
            "architecture": {
                "service_layer": "enabled",
                "event_driven": "enabled",
                "repository_pattern": "enabled",
            },
            "event_bus": {"status": event_status, "statistics": event_stats},
            "features": [
                "Enhanced error handling",
                "Request validation",
                "Structured responses",
                "Health monitoring",
                "Request tracking",
                "Service layer architecture",
                "Event-driven processing",
                "Multi-channel notifications",
            ],
            "endpoints": {
                "health": "/api/v1/health",
                "stocks": "/api/v1/stocks",
                "tracking": "/api/v1/tracking",
                "alerts": "/api/v1/alerts",
                "notifications": "/api/v1/notifications",
                "system": "/api/v1/system",
                "webhook": "/webhook/tg-nqlftdvdqi",
                "docs": "/docs",
            },
        }

        return StatusResponse.create(data=status_data, request_id=request_id)

    # Enhanced exception handlers for custom exceptions
    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        """Handle validation exceptions."""
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            "Validation exception occurred",
            error=str(exc),
            path=request.url.path,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                success=False,
                error={
                    "type": "ValidationError",
                    "message": str(exc),
                    "status_code": 400,
                },
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(NotFoundError)
    async def not_found_exception_handler(request: Request, exc: NotFoundError):
        """Handle not found exceptions."""
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            "Not found exception occurred",
            error=str(exc),
            path=request.url.path,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                success=False,
                error={
                    "type": "NotFoundError",
                    "message": str(exc),
                    "status_code": 404,
                },
                request_id=request_id,
            ).model_dump(),
        )

    @app.post(
        "/webhook/tg-nqlftdvdqi",
        response_model=StatusResponse,
        summary="Telegram Webhook",
        description="Handle incoming Telegram webhook updates",
    )
    async def telegram_webhook(request: Request):
        """
        Handle incoming Telegram webhook updates with enhanced error handling.

        This endpoint receives updates from Telegram when users send messages.
        Uses X-Telegram-Bot-Api-Secret-Token header for authentication.
        """
        request_id = request.state.request_id

        # Verify Telegram webhook authentication, return 404 if invalid
        if not verify_telegram_webhook_auth(request):
            logger.warning("Unauthorized webhook attempt", request_id=request_id)
            raise HTTPException(status_code=404, detail="Not Found")

        try:
            update: Dict[str, Any] = await request.json()

            # Extract message information
            text, chat_id, user_id = telegram_bot.extract_message_info(update)

            if not text or not chat_id:
                logger.debug(
                    "Webhook update ignored - no text or chat_id", request_id=request_id
                )
                return StatusResponse.create(
                    data={"status": "ignored", "reason": "No text or chat_id"},
                    request_id=request_id,
                )

            # Check if message is from authorized user
            if chat_id != settings.telegram_chat_id:
                logger.warning(
                    "Unauthorized message attempt",
                    received_chat_id=chat_id,
                    authorized_chat_id=settings.telegram_chat_id,
                    request_id=request_id,
                )
                await telegram_bot.send_message(
                    "Sorry, you are not authorized to use this bot.", chat_id=chat_id
                )
                return StatusResponse.create(
                    data={"status": "unauthorized"}, request_id=request_id
                )

            logger.info(
                "Processing Telegram message",
                chat_id=chat_id,
                message_length=len(text),
                request_id=request_id,
            )

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

            logger.info(
                "Telegram message processed successfully", request_id=request_id
            )
            return StatusResponse.create(
                data={
                    "status": "processed",
                    "message_length": len(text),
                    "response_sent": True,
                },
                request_id=request_id,
            )

        except Exception as e:
            logger.error(
                "Error processing Telegram webhook",
                error=str(e),
                request_id=request_id,
                exc_info=True,
            )
            return StatusResponse.create(
                data={"status": "error", "error": str(e)}, request_id=request_id
            )

    @app.post(
        "/webhook/set",
        response_model=StatusResponse,
        summary="Set Webhook",
        description="Configure Telegram webhook URL",
    )
    async def set_webhook(
        request: Request, webhook_url: str, token: str = Depends(verify_auth_token)
    ) -> StatusResponse:
        """
        Set the Telegram webhook URL with enhanced response handling.

        Args:
            request: The incoming request
            webhook_url: The URL where Telegram should send updates
            token: Authentication token (provided via Authorization header)
        """
        request_id = request.state.request_id

        try:
            logger.info(
                "Setting Telegram webhook",
                webhook_url=webhook_url,
                request_id=request_id,
            )

            # Use the same token for webhook secret authentication
            auth_token = os.getenv("TELEGRAM_AUTH_TOKEN")
            success = await telegram_bot.set_webhook(
                webhook_url, secret_token=auth_token
            )

            if success:
                logger.info("Webhook set successfully", request_id=request_id)
                return StatusResponse.create(
                    data={
                        "status": "webhook_set",
                        "url": webhook_url,
                        "secret_token_configured": bool(auth_token),
                    },
                    request_id=request_id,
                )
            else:
                logger.error("Failed to set webhook", request_id=request_id)
                raise HTTPException(status_code=400, detail="Failed to set webhook")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Error setting webhook",
                error=str(e),
                request_id=request_id,
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail=f"Error setting webhook: {e}")

    @app.get(
        "/webhook/info",
        response_model=StatusResponse,
        summary="Webhook Info",
        description="Get current webhook configuration",
    )
    async def get_webhook_info(
        request: Request, token: str = Depends(verify_auth_token)
    ) -> StatusResponse:
        """
        Get current webhook information with enhanced response model.

        Args:
            request: The incoming request
            token: Authentication token (provided via Authorization header)
        """
        request_id = request.state.request_id

        try:
            logger.info("Getting webhook info", request_id=request_id)
            info = await telegram_bot.get_webhook_info()

            return StatusResponse.create(
                data={"webhook_info": info}, request_id=request_id
            )

        except Exception as e:
            logger.error(
                "Error getting webhook info",
                error=str(e),
                request_id=request_id,
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Error getting webhook info: {e}"
            )

    @app.delete(
        "/webhook",
        response_model=StatusResponse,
        summary="Delete Webhook",
        description="Remove current webhook configuration",
    )
    async def delete_webhook(
        request: Request, token: str = Depends(verify_auth_token)
    ) -> StatusResponse:
        """
        Delete the current webhook with enhanced response handling.

        Args:
            request: The incoming request
            token: Authentication token (provided via Authorization header)
        """
        request_id = request.state.request_id

        try:
            logger.info("Deleting webhook", request_id=request_id)
            success = await telegram_bot.delete_webhook()

            if success:
                logger.info("Webhook deleted successfully", request_id=request_id)
                return StatusResponse.create(
                    data={"status": "webhook_deleted"}, request_id=request_id
                )
            else:
                logger.error("Failed to delete webhook", request_id=request_id)
                raise HTTPException(status_code=400, detail="Failed to delete webhook")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Error deleting webhook",
                error=str(e),
                request_id=request_id,
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail=f"Error deleting webhook: {e}")

    logger.info("FastAPI application created with enhanced architecture")
    return app


# Create the app instance
app = create_app()
