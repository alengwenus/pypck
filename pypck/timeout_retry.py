"""Base classes for handling reoccurent tasks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pypck.helpers import TaskRegistry, cancel_task

_LOGGER = logging.getLogger(__name__)

# The default timeout to use for requests. Worst case: Requesting threshold
# 4-4 takes at least 1.8s
DEFAULT_TIMEOUT = 3.5


class TimeoutRetryHandler:
    """Manage timeout and retry logic for an LCN request."""

    def __init__(
        self,
        task_registry: TaskRegistry,
        num_tries: int = 3,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Construct TimeoutRetryHandler."""
        self.task_registry = task_registry
        self.num_tries = num_tries
        self.timeout = timeout
        self._timeout_callback: (
            Callable[..., None] | Callable[..., Awaitable[None]] | None
        ) = None
        self._timeout_args: tuple[Any, ...] = ()
        self._timeout_kwargs: dict[str, Any] = {}
        self.timeout_loop_task: asyncio.Task[None] | None = None

    def set_timeout(self, timeout: int) -> None:
        """Set the timeout in seconds."""
        self.timeout = timeout

    def set_timeout_callback(
        self, timeout_callback: Any, *timeout_args: Any, **timeout_kwargs: Any
    ) -> None:
        """Timeout_callback function is called, if timeout expires.

        Function has to take one argument:
        Returns failed state (True if failed)
        """
        self._timeout_callback = timeout_callback
        self._timeout_args = timeout_args
        self._timeout_kwargs = timeout_kwargs

    def activate(self) -> None:
        """Schedule the next activation."""
        self.task_registry.create_task(self.async_activate())

    async def async_activate(self) -> None:
        """Clean start of next timeout_loop."""
        if self.is_active():
            return
        self.timeout_loop_task = self.task_registry.create_task(self.timeout_loop())

    async def done(self) -> None:
        """Signal the completion of the TimeoutRetryHandler."""
        if self.timeout_loop_task is not None:
            await self.timeout_loop_task

    async def cancel(self) -> None:
        """Must be called when a response (requested or not) is received."""
        if self.timeout_loop_task is not None:
            await cancel_task(self.timeout_loop_task)

    def is_active(self) -> bool:
        """Check whether the request logic is active."""
        if self.timeout_loop_task is None:
            return False
        return not self.timeout_loop_task.done()

    async def on_timeout(self, failed: bool = False) -> None:
        """Is called on timeout of TimeoutRetryHandler."""
        if self._timeout_callback is not None:
            if asyncio.iscoroutinefunction(self._timeout_callback):
                # mypy fails to notice that `asyncio.iscoroutinefunction`
                # separates await-callable from ordinary callables.
                await self._timeout_callback(
                    failed, *self._timeout_args, **self._timeout_kwargs
                )
            else:
                self._timeout_callback(
                    failed, *self._timeout_args, **self._timeout_kwargs
                )

    async def timeout_loop(self) -> None:
        """Timeout / retry loop."""
        if self.timeout_loop_task is None:
            return
        tries_left = self.num_tries
        while (tries_left > 0) or (tries_left == -1):
            if not self.timeout_loop_task.done():
                await self.on_timeout()
                await asyncio.sleep(self.timeout)
                if self.num_tries != -1:
                    tries_left -= 1
            else:
                break

        if not self.timeout_loop_task.done():
            await self.on_timeout(failed=True)
