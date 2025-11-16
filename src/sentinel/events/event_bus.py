"""Event bus for managing and dispatching domain events."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ..config.logging import get_logger
from .events import DomainEvent

logger = get_logger(__name__)


class EventBus:
    """Event bus for publishing and subscribing to domain events."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.logger = logger.bind(event_bus=name)

        # Event handlers registry: event_type -> list of handlers
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = defaultdict(list)

        # Event history for debugging and monitoring
        self._event_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000

        # Event statistics
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "handlers_executed": 0,
            "errors_count": 0,
            "last_event_time": None,
        }

        self.logger.info("Event bus initialized", name=name)

    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], Union[None, asyncio.Task]],
    ) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function (sync or async)
        """
        self._handlers[event_type].append(handler)

        self.logger.info(
            "Event handler subscribed",
            event_type=event_type.__name__,
            handler=handler.__name__,
            total_handlers=len(self._handlers[event_type]),
        )

    def unsubscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], Union[None, asyncio.Task]],
    ) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove

        Returns:
            True if handler was found and removed
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

            self.logger.info(
                "Event handler unsubscribed",
                event_type=event_type.__name__,
                handler=handler.__name__,
                remaining_handlers=len(self._handlers[event_type]),
            )
            return True

        return False

    async def publish(
        self, event: DomainEvent, wait_for_handlers: bool = False
    ) -> Dict[str, Any]:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: Domain event to publish
            wait_for_handlers: Whether to wait for all handlers to complete

        Returns:
            Dictionary with publication results
        """
        start_time = datetime.utcnow()
        event_type = type(event)

        self.logger.info(
            "Publishing event",
            event_type=event_type.__name__,
            event_id=event.event_id,
            wait_for_handlers=wait_for_handlers,
        )

        # Update statistics
        self._stats["events_published"] += 1
        self._stats["last_event_time"] = start_time

        # Record event in history
        self._add_to_history(event, "published")

        # Get handlers for this event type
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            self.logger.debug(
                "No handlers registered for event type", event_type=event_type.__name__
            )
            return {
                "event_id": event.event_id,
                "handlers_executed": 0,
                "successful_handlers": 0,
                "failed_handlers": 0,
                "execution_time_ms": 0,
            }

        # Execute handlers
        results = await self._execute_handlers(event, handlers, wait_for_handlers)

        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        self.logger.info(
            "Event publishing completed",
            event_type=event_type.__name__,
            event_id=event.event_id,
            handlers_executed=results["handlers_executed"],
            successful_handlers=results["successful_handlers"],
            failed_handlers=results["failed_handlers"],
            execution_time_ms=execution_time,
        )

        results["execution_time_ms"] = execution_time
        return results

    async def _execute_handlers(
        self, event: DomainEvent, handlers: List[Callable], wait_for_completion: bool
    ) -> Dict[str, Any]:
        """
        Execute all handlers for an event.

        Args:
            event: Event to handle
            handlers: List of handler functions
            wait_for_completion: Whether to wait for completion

        Returns:
            Execution results dictionary
        """
        tasks = []
        successful_handlers = 0
        failed_handlers = 0

        for handler in handlers:
            try:
                # Check if handler is async
                if asyncio.iscoroutinefunction(handler):
                    task = asyncio.create_task(handler(event))
                else:
                    # Wrap sync handler in async task
                    task = asyncio.create_task(asyncio.to_thread(handler, event))

                tasks.append(task)

            except Exception as e:
                failed_handlers += 1
                self._stats["errors_count"] += 1

                self.logger.error(
                    "Failed to create handler task",
                    event_type=type(event).__name__,
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True,
                )

        # Execute tasks
        if tasks:
            if wait_for_completion:
                # Wait for all handlers to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_handlers += 1
                        self._stats["errors_count"] += 1

                        self.logger.error(
                            "Handler execution failed",
                            event_type=type(event).__name__,
                            handler=(
                                handlers[i].__name__ if i < len(handlers) else "unknown"
                            ),
                            error=str(result),
                            exc_info=True,
                        )
                    else:
                        successful_handlers += 1
            else:
                # Fire and forget - don't wait for completion
                successful_handlers = len(tasks)

        self._stats["handlers_executed"] += len(handlers)
        self._stats["events_processed"] += 1

        return {
            "event_id": event.event_id,
            "handlers_executed": len(handlers),
            "successful_handlers": successful_handlers,
            "failed_handlers": failed_handlers,
        }

    def _add_to_history(self, event: DomainEvent, action: str):
        """Add event to history for debugging."""
        history_entry = {
            "action": action,
            "event_type": type(event).__name__,
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "recorded_at": datetime.utcnow().isoformat(),
        }

        self._event_history.append(history_entry)

        # Maintain history size limit
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size :]

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        handler_counts = {
            event_type.__name__: len(handlers)
            for event_type, handlers in self._handlers.items()
        }

        return {
            **self._stats,
            "registered_event_types": len(self._handlers),
            "total_handlers": sum(
                len(handlers) for handlers in self._handlers.values()
            ),
            "handlers_by_event_type": handler_counts,
            "history_size": len(self._event_history),
        }

    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent event history."""
        return self._event_history[-limit:] if self._event_history else []

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
        self.logger.info("Event history cleared")

    def get_handlers_for_event(self, event_type: Type[DomainEvent]) -> List[str]:
        """Get list of handler names for an event type."""
        handlers = self._handlers.get(event_type, [])
        return [handler.__name__ for handler in handlers]


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _global_event_bus

    if _global_event_bus is None:
        _global_event_bus = EventBus("global")

    return _global_event_bus


def set_event_bus(event_bus: EventBus):
    """Set the global event bus instance."""
    global _global_event_bus
    _global_event_bus = event_bus
