"""Helper functions for pypck."""

import asyncio
from collections.abc import Coroutine
from typing import Any


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


class TaskRegistry:
    """Keep track of running tasks."""

    def __init__(self) -> None:
        """Init task registry instance."""
        self.tasks: list["asyncio.Task[Any]"] = []

    def remove_task(self, task: "asyncio.Task[None]") -> None:
        """Remove a task from the task registry."""
        if task in self.tasks:
            self.tasks.remove(task)

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> "asyncio.Task[None]":
        """Create a task and store a reference in the task registry."""
        task: asyncio.Task[Any] = asyncio.create_task(coro)
        task.add_done_callback(self.remove_task)
        self.tasks.append(task)
        return task

    async def cancel_all_tasks(self) -> None:
        """Cancel all pypck tasks."""
        while self.tasks:
            await cancel_task(self.tasks.pop())
