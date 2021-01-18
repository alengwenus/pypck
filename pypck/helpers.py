"""Helper functions for pypck."""

import asyncio
from typing import Any, Awaitable, List, Optional

PYPCK_TASKS: List["asyncio.Task[Any]"] = []


def create_task(coro: Awaitable[Any]) -> "asyncio.Task[None]":
    """Create a task and store a reference in the task registry.

    If shield is True, the task is shielded from cancellation.
    """
    task = asyncio.create_task(coro)
    task.add_done_callback(PYPCK_TASKS.remove)
    PYPCK_TASKS.append(task)
    return task


async def cancel_task(task: "asyncio.Task[Any]") -> bool:
    """Cancel a task.

    Wait for cancellation completed but do not propagate a possible CancelledError.
    """
    success = task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    return success  # was not already done


async def cancel_all_tasks() -> None:
    """Cancel all pypck tasks."""
    while PYPCK_TASKS:
        await cancel_task(PYPCK_TASKS.pop())


class PchkLicenseError(Exception):
    """Exception which is raised if a license error occurred."""

    def __init__(self, message: Optional[str] = None):
        """Initialize instance."""
        if message is None:
            message = (
                "Maximum number of connections was reached. An "
                "additional license key is required."
            )
        super().__init__(message)


class PchkAuthenticationError(Exception):
    """Exception which is raised if authentication failed."""

    def __init__(self, message: Optional[str] = None):
        """Initialize instance."""
        if message is None:
            message = "Authentication failed."
        super().__init__(message)


class PchkLcnNotConnectedError(Exception):
    """Exception which is raised if there is no connection to the LCN bus."""

    def __init__(self, message: Optional[str] = None):
        """Initialize instance."""
        if message is None:
            message = "LCN not connected."
        super().__init__(message)
