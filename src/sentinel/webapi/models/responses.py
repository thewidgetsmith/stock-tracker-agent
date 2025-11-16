"""Response models for the Sentinel API."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, field_serializer

# Generic type for data responses
T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model for all API responses."""

    success: bool = Field(..., description="Whether the request was successful")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    request_id: Optional[str] = Field(
        None, description="Unique request identifier for tracking"
    )

    model_config = ConfigDict(
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        """Serialize datetime to ISO format with Z suffix."""
        return dt.isoformat() + "Z"


class SuccessResponse(BaseResponse, Generic[T]):
    """Generic success response with typed data."""

    success: bool = Field(True, description="Always true for success responses")
    data: T = Field(..., description="Response data")
    message: Optional[str] = Field(None, description="Optional success message")


class ErrorResponse(BaseResponse):
    """Error response model."""

    success: bool = Field(False, description="Always false for error responses")
    error: Dict[str, Any] = Field(..., description="Error details")

    @classmethod
    def from_exception(
        cls, exc: Exception, request_id: Optional[str] = None
    ) -> "ErrorResponse":
        """Create error response from exception."""
        return cls(
            success=False,
            error={
                "type": type(exc).__name__,
                "message": str(exc),
                "details": getattr(exc, "detail", None),
            },
            request_id=request_id,
        )


class HealthStatus(BaseModel):
    """Health status model."""

    status: str = Field(
        ..., description="Overall health status: healthy, degraded, unhealthy"
    )
    services: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Individual service statuses"
    )
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    version: Optional[str] = Field(None, description="Application version")


class HealthResponse(BaseResponse):
    """Health check response."""

    success: bool = Field(True, description="Always true for health responses")
    health: HealthStatus = Field(..., description="Detailed health information")


class StockPrice(BaseModel):
    """Stock price information."""

    symbol: str = Field(..., description="Stock symbol")
    current_price: float = Field(..., description="Current stock price")
    previous_close: Optional[float] = Field(None, description="Previous closing price")
    change: Optional[float] = Field(None, description="Price change amount")
    change_percent: Optional[float] = Field(None, description="Price change percentage")
    volume: Optional[int] = Field(None, description="Trading volume")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow, description="Last updated timestamp"
    )


class StockDataResponse(SuccessResponse[StockPrice]):
    """Response model for stock data."""

    data: StockPrice = Field(..., description="Stock price data")


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """Alert model."""

    id: str = Field(..., description="Unique alert identifier")
    symbol: str = Field(..., description="Stock symbol")
    level: AlertLevel = Field(..., description="Alert severity level")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    trigger_price: Optional[float] = Field(
        None, description="Price that triggered the alert"
    )
    current_price: Optional[float] = Field(
        None, description="Current stock price when alert was created"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Alert creation timestamp"
    )
    acknowledged: bool = Field(False, description="Whether alert has been acknowledged")
    acknowledged_at: Optional[datetime] = Field(
        None, description="Alert acknowledgment timestamp"
    )


class AlertResponse(SuccessResponse[Alert]):
    """Response model for single alert."""

    data: Alert = Field(..., description="Alert data")


class AlertListResponse(SuccessResponse[List[Alert]]):
    """Response model for alert list."""

    data: List[Alert] = Field(..., description="List of alerts")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedData(BaseModel, Generic[T]):
    """Paginated data container."""

    items: List[T] = Field(..., description="List of items for current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class PaginatedResponse(SuccessResponse[PaginatedData[T]]):
    """Response model for paginated data."""

    data: PaginatedData[T] = Field(..., description="Paginated data with metadata")


# Utility response models
class MessageResponse(SuccessResponse[Dict[str, str]]):
    """Simple message response."""

    data: Dict[str, str] = Field(..., description="Message data")

    @classmethod
    def create(
        cls, message: str, request_id: Optional[str] = None
    ) -> "MessageResponse":
        """Create a simple message response."""
        return cls(
            success=True,
            data={"message": message},
            message=message,
            request_id=request_id,
        )


class StatusResponse(SuccessResponse[Dict[str, Any]]):
    """Generic status response."""

    data: Dict[str, Any] = Field(..., description="Status data")

    @classmethod
    def create(
        cls,
        data: Dict[str, Any],
        message: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> "StatusResponse":
        """Create a status response."""
        return cls(success=True, data=data, message=message, request_id=request_id)
