"""Connection tests."""
from unittest.mock import Mock

from pypck.pck_commands import PckParser
from tests.conftest import PASSWORD, USERNAME, encode_pck

# Socket connection tests


def test_called_connection_made(pchk_connection_manager):
    """Test if socket_connected future is done.

    Connection to socket is already established.
    """
    pchk_connection_manager.connect()
    assert pchk_connection_manager.socket_connected.done()


def test_async_connect(monkeypatch, loop, pchk_connection_manager):
    """Tests if async_connect coroutine continues.

    All connection futures are done previously.
    """
    monkeypatch.setattr(pchk_connection_manager, 'connect', Mock())
    pchk_connection_manager.socket_connected.set_result(True)
    pchk_connection_manager.lcn_connected.set_result(True)
    pchk_connection_manager.segment_scan_completed.set_result(True)
    loop.run_until_complete(
        pchk_connection_manager.async_connect(timeout=0.5))
    assert pchk_connection_manager.connect.called

# Authentication tests


def test_received_auth_username(pchk_connection_manager):
    """Test username authentication workflow."""
    pchk_connection_manager.data_received(
        encode_pck(PckParser.AUTH_USERNAME))
    pchk_connection_manager.send_command.assert_called_with(USERNAME)


def test_received_auth_password(pchk_connection_manager):
    """Test password authentication workflow."""
    pchk_connection_manager.data_received(
        encode_pck(PckParser.AUTH_PASSWORD))
    pchk_connection_manager.send_command.assert_called_with(PASSWORD)


def test_received_auth_ok(monkeypatch, pchk_connection_manager):
    """Test authentication ok workflow."""
    monkeypatch.setattr(pchk_connection_manager, 'on_auth_ok', Mock())
    pchk_connection_manager.data_received(
        encode_pck(PckParser.AUTH_OK))
    assert pchk_connection_manager.on_auth_ok.called

# LCN Connection tests


def test_received_lcn_connected(monkeypatch, pchk_connection_manager):
    """Test if correct workflow is done.

    LCN connected message is already received.
    """
    monkeypatch.setattr(pchk_connection_manager, 'on_successful_login', Mock())
    pchk_connection_manager.data_received(
        encode_pck(PckParser.LCNCONNSTATE_CONNECTED))
    assert pchk_connection_manager.on_successful_login.called

    pchk_connection_manager.send_command.assert_called_with('!OM0P')


def test_called_on_successful_login(monkeypatch, pchk_connection_manager):
    """Test workflow after on_successful_login was called.

    (E.g. lcn_connected future is done, ping procedure started, segment scan
    started).
    """
    with monkeypatch.context() as mpc:
        mpc.setattr(pchk_connection_manager, 'ping', Mock())
        mpc.setattr(pchk_connection_manager, 'status_segment_scan', Mock())
        pchk_connection_manager.on_successful_login()

        # assert that lcn_connected future has result set
        assert pchk_connection_manager.lcn_connected.done()

        # assert that TimeoutRetryhandlers for ping and segment_scans are
        # activated
        assert pchk_connection_manager.ping.activate.called
        assert pchk_connection_manager.status_segment_scan.activate.called

# LCN segment scan tests


def test_called_segment_scan(monkeypatch, pchk_connection_manager):
    """Test workflow after segment_scan completed (not) successful."""
    monkeypatch.setattr(pchk_connection_manager, 'set_local_seg_id', Mock())
    # assert that for each timeout a segment scan command is sent
    pchk_connection_manager.segment_scan_timeout(False)
    pchk_connection_manager.send_command.assert_called_with('>G003003.SK')

    # assert that if max retries is reached, local segment id is set to 0
    pchk_connection_manager.segment_scan_timeout(True)
    pchk_connection_manager.set_local_seg_id.assert_called_with(0)


def test_received_segment_info(monkeypatch, pchk_connection_manager):
    """Test if local segment id is about to set.

    Appropriate PCK command was received previously.
    """
    monkeypatch.setattr(pchk_connection_manager, 'set_local_seg_id', Mock())
    pck = '=M000005.SK7'
    pchk_connection_manager.data_received(encode_pck(pck))

    # assert that local segment id is set properly
    pchk_connection_manager.set_local_seg_id.assert_called_with(7)


def test_called_local_seg_id(pchk_connection_manager):
    """Test if local segment id was set correctly.

    Set_local_seg_id was called previously.
    """
    pchk_connection_manager.set_local_seg_id(7)

    assert pchk_connection_manager.local_seg_id == 7
    assert pchk_connection_manager.segment_scan_completed.done()
