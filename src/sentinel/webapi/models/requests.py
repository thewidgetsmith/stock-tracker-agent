"""Request models for the Sentinel API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class StockSymbolRequest(BaseModel):
    """Request model for stock symbol operations."""

    symbol: str = Field(
        ..., description="Stock symbol (e.g., AAPL, GOOGL)", min_length=1, max_length=10
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        if not v.isalpha():
            raise ValueError("Symbol must contain only letters")
        return v.upper()


class AlertCreateRequest(BaseModel):
    """Request model for creating stock price alerts."""

    symbol: str = Field(
        ..., description="Stock symbol to monitor", min_length=1, max_length=10
    )
    alert_type: str = Field(
        ..., description="Type of alert: above, below, change_percent"
    )
    threshold: float = Field(
        ..., description="Price threshold or percentage change threshold"
    )
    message: Optional[str] = Field(
        None, description="Custom alert message", max_length=500
    )
    enabled: bool = Field(True, description="Whether the alert is active")

    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        if not v.isalpha():
            raise ValueError("Symbol must contain only letters")
        return v.upper()

    @validator("alert_type")
    def validate_alert_type(cls, v):
        """Validate alert type."""
        valid_types = ["above", "below", "change_percent"]
        if v.lower() not in valid_types:
            raise ValueError(f"Alert type must be one of: {', '.join(valid_types)}")
        return v.lower()

    @validator("threshold")
    def validate_threshold(cls, v, values):
        """Validate threshold based on alert type."""
        if v <= 0:
            raise ValueError("Threshold must be positive")

        alert_type = values.get("alert_type")
        if alert_type == "change_percent" and v > 100:
            raise ValueError("Percentage change threshold cannot exceed 100%")

        return v


class AlertUpdateRequest(BaseModel):
    """Request model for updating alerts."""

    threshold: Optional[float] = Field(None, description="New price threshold")
    message: Optional[str] = Field(
        None, description="Updated alert message", max_length=500
    )
    enabled: Optional[bool] = Field(None, description="Whether the alert is active")
    acknowledged: Optional[bool] = Field(None, description="Mark alert as acknowledged")

    @validator("threshold")
    def validate_threshold(cls, v):
        """Validate threshold value."""
        if v is not None and v <= 0:
            raise ValueError("Threshold must be positive")
        return v


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(10, ge=1, le=100, description="Number of items per page")

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class AlertFilterParams(BaseModel):
    """Filter parameters for alert listing."""

    symbol: Optional[str] = Field(None, description="Filter by stock symbol")
    level: Optional[str] = Field(None, description="Filter by alert level")
    acknowledged: Optional[bool] = Field(
        None, description="Filter by acknowledgment status"
    )
    created_after: Optional[datetime] = Field(
        None, description="Filter alerts created after this date"
    )
    created_before: Optional[datetime] = Field(
        None, description="Filter alerts created before this date"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        if v and not v.isalpha():
            raise ValueError("Symbol must contain only letters")
        return v.upper() if v else v

    @validator("level")
    def validate_level(cls, v):
        """Validate alert level."""
        if v:
            valid_levels = ["info", "warning", "error", "critical"]
            if v.lower() not in valid_levels:
                raise ValueError(f"Level must be one of: {', '.join(valid_levels)}")
            return v.lower()
        return v


class HealthCheckRequest(BaseModel):
    """Request model for health checks."""

    include_services: bool = Field(
        True, description="Include individual service health checks"
    )
    detailed: bool = Field(False, description="Include detailed system information")


class StockAnalysisRequest(BaseModel):
    """Request model for stock analysis."""

    symbol: str = Field(
        ..., description="Stock symbol to analyze", min_length=1, max_length=10
    )
    period: str = Field(
        "1d", description="Analysis period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y"
    )
    include_technical: bool = Field(
        False, description="Include technical analysis indicators"
    )
    include_fundamentals: bool = Field(
        False, description="Include fundamental analysis data"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        if not v.isalpha():
            raise ValueError("Symbol must contain only letters")
        return v.upper()

    @validator("period")
    def validate_period(cls, v):
        """Validate analysis period."""
        valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y"]
        if v.lower() not in valid_periods:
            raise ValueError(f"Period must be one of: {', '.join(valid_periods)}")
        return v.lower()


class NotificationRequest(BaseModel):
    """Request model for sending notifications."""

    symbol: str = Field(..., description="Stock symbol", min_length=1, max_length=10)
    message: str = Field(
        ..., description="Notification message", min_length=1, max_length=1000
    )
    priority: str = Field(
        "normal", description="Notification priority: low, normal, high, urgent"
    )
    channels: list[str] = Field(
        ["telegram"], description="Notification channels to use"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        if not v.isalpha():
            raise ValueError("Symbol must contain only letters")
        return v.upper()

    @validator("priority")
    def validate_priority(cls, v):
        """Validate notification priority."""
        valid_priorities = ["low", "normal", "high", "urgent"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
        return v.lower()

    @validator("channels")
    def validate_channels(cls, v):
        """Validate notification channels."""
        valid_channels = ["telegram", "email", "sms", "webhook"]
        invalid_channels = [ch for ch in v if ch.lower() not in valid_channels]
        if invalid_channels:
            raise ValueError(f"Invalid channels: {', '.join(invalid_channels)}")
        return [ch.lower() for ch in v]
