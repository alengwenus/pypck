'''
Copyright (c) 2006-2018 by the respective copyright holders.

All rights reserved. This program and the accompanying materials
are made available under the terms of the Eclipse Public License v1.0
which accompanies this distribution, and is available at
http://www.eclipse.org/legal/epl-v10.html

Contributors:
  Andre Lengwenus - port to Python and further improvements
  Tobias Juettner - initial LCN binding for openHAB (Java)
'''

import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

# The default timeout to use for requests. Worst case: Requesting threshold
# 4-4 takes at least 1.8s
DEFAULT_TIMEOUT_MSEC = 3500


class TimeoutRetryHandler():
    """Manages timeout and retry logic for an LCN request.

    :param           loop:           The asyncio event loop
    :param    int    num_tries:      The maximum number of tries until the
                                     request is marked as failed (-1 means
                                     forever)
    :param    int    timeout_msec:   Default timeout in milliseconds

    """

    def __init__(self, loop, num_tries=3, timeout_msec=DEFAULT_TIMEOUT_MSEC):
        """Constructor.
        """
        self.loop = loop
        self.num_tries = num_tries
        self.timeout_msec = timeout_msec
        self._timeout_callback = None
        self.timeout_loop_task = None

    def set_timeout_msec(self, timeout_msec):
        """Set the timeout in milliseconds.

        :param    int    timeout_msec:    The timeout in milliseconds
        """
        self.timeout_msec = timeout_msec

    def set_timeout_callback(self, timeout_callback):
        """Timeout_callback function is called, if timeout expires.
        Function has to take one argument:
        Returns failed state (True if failed)
        """
        self._timeout_callback = timeout_callback

    def activate(self, timeout_callback=None):
        """Schedules the next request.
        """
        if self.is_active():
            self.loop.create_task(self.cancel())
        if timeout_callback is not None:
            self.set_timeout_callback(timeout_callback)

        self.timeout_loop_task = self.loop.create_task(self.timeout_loop())

    async def done(self):
        """Signals the completion of the TimeoutRetryHandler.
        """
        await self.timeout_loop_task

    async def cancel(self):
        """Must be called when a response (requested or not) has been
        received.
        """
        if self.timeout_loop_task is not None:
            self.timeout_loop_task.cancel()
            try:
                await self.timeout_loop_task
            except asyncio.CancelledError:
                pass

    def is_active(self):
        """Checks whether the request logic is active.
        """
        if self.timeout_loop_task is None:
            return False
        return not self.timeout_loop_task.done()

    async def on_timeout(self, failed=False):
        """Callback which is called on timeout of TimeoutRetryHandler.
        """
        if self._timeout_callback is not None:
            self._timeout_callback(failed)

    async def timeout_loop(self):
        """Timeout / retry loop.
        """
        tries_left = self.num_tries
        while (tries_left > 0) or (tries_left == -1):
            if not self.timeout_loop_task.done():
                await self.on_timeout()
                await asyncio.sleep(self.timeout_msec / 1000)
                if self.num_tries != -1:
                    tries_left -= 1
            else:
                break

        if not self.timeout_loop_task.done():
            await self.on_timeout(failed=True)
