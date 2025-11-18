"""Test the status requester of a module connection."""

import asyncio
from unittest.mock import call

from pypck.pck_commands import PckGenerator
from pypck.status_requester import StatusRequest

from pypck import inputs

from .conftest import MockDeviceConnection

RELAY_STATES = [True, False, True, False, True, False, True, False]


async def test_request_status(module10: MockDeviceConnection) -> None:
    """Test requesting the status of a module."""
    request_task = asyncio.create_task(
        module10.status_requester.request(
            response_type=inputs.ModStatusRelays,
            request_pck=PckGenerator.request_relays_status(),
            max_age=0,
        )
    )
    await asyncio.sleep(0)

    module10.send_command.assert_awaited_with(
        False, PckGenerator.request_relays_status()
    )

    await module10.async_process_input(
        inputs.ModStatusRelays(module10.addr, RELAY_STATES)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusRelays)
    assert result.physical_source_addr == module10.addr
    assert result.states == RELAY_STATES


async def test_request_status_stored(module10: MockDeviceConnection) -> None:
    """Test requesting the status of a module with stored status request."""
    status_request = StatusRequest(
        type=inputs.ModStatusRelays,
        parameters=frozenset(),
        timestamp=asyncio.get_running_loop().time(),
        response=asyncio.get_running_loop().create_future(),
    )
    status_request.response.set_result(
        inputs.ModStatusRelays(module10.addr, RELAY_STATES)
    )
    module10.status_requester.last_requests.add(status_request)

    result = await module10.status_requester.request(
        response_type=inputs.ModStatusRelays,
        request_pck=PckGenerator.request_relays_status(),
        max_age=10,
    )

    assert isinstance(result, inputs.ModStatusRelays)
    assert result.physical_source_addr == module10.addr
    assert result.states == RELAY_STATES
    assert (
        call(False, PckGenerator.request_relays_status())
        not in module10.send_command.await_args_list
    )


async def test_request_status_expired(module10: MockDeviceConnection) -> None:
    """Test requesting the status of a module with stored status request but max_age expired."""
    states = [False] * 8
    status_request = StatusRequest(
        type=inputs.ModStatusRelays,
        parameters=frozenset(),
        timestamp=asyncio.get_running_loop().time() - 10,
        response=asyncio.get_running_loop().create_future(),
    )
    status_request.response.set_result(inputs.ModStatusRelays(module10.addr, states))
    module10.status_requester.last_requests.add(status_request)

    request_task = asyncio.create_task(
        module10.status_requester.request(
            response_type=inputs.ModStatusRelays,
            request_pck=PckGenerator.request_relays_status(),
            max_age=5,
        )
    )
    await asyncio.sleep(0)

    module10.send_command.assert_awaited_with(
        False, PckGenerator.request_relays_status()
    )

    await module10.async_process_input(
        inputs.ModStatusRelays(module10.addr, RELAY_STATES)
    )

    result = await request_task

    assert isinstance(result, inputs.ModStatusRelays)
    assert result.physical_source_addr == module10.addr
    assert result.states == RELAY_STATES
