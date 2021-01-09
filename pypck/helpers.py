"""Helper functions for pypck."""

import asyncio
from typing import Any, Awaitable, List

PYPCK_TASKS: List["asyncio.Task[Any]"] = []


def create_task(coro: Awaitable[Any]) -> "asyncio.Task[None]":
    """Create a task and store a reference in the task registry."""
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
    for task in tuple(PYPCK_TASKS):
        await cancel_task(task)
