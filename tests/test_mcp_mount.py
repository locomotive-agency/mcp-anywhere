import asyncio
import contextlib
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from mcp_anywhere.web.mcp_mount import (
    FastMCPLifespanWrapper,
    create_mcp_mount_with_lifespan,
)


@pytest.mark.asyncio
async def test_wrapper_initialization():
    """Verify that FastMCPLifespanWrapper initializes its internal state correctly."""

    mock_app = Mock()
    wrapper = FastMCPLifespanWrapper(mock_app)

    assert wrapper.fastmcp_app is mock_app
    assert wrapper.lifespan_task is None
    assert wrapper.lifespan_started is False
    assert isinstance(wrapper.startup_event, asyncio.Event)
    assert isinstance(wrapper.shutdown_event, asyncio.Event)


@pytest.mark.asyncio
async def test_first_request_starts_lifespan():

    mock_app = AsyncMock()
    wrapper = FastMCPLifespanWrapper(mock_app)

    scope = {"type": "http", "path": "/"}
    receive = AsyncMock()
    send = AsyncMock()

    with patch.object(wrapper, "_ensure_lifespan_started", new=AsyncMock()) as mock_ensure:
        await wrapper(scope, receive, send)
        mock_ensure.assert_called_once()
        mock_app.assert_called_once_with(scope, receive, send)


@pytest.mark.asyncio
async def test_multiple_requests_do_not_restart_lifespan():

    mock_app = AsyncMock()
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch.object(wrapper, "_ensure_lifespan_started", new=AsyncMock()) as mock_ensure:

        wrapper.lifespan_started = True

        scope = {"type": "http", "path": "/"}
        receive = AsyncMock()
        send = AsyncMock()

        await wrapper(scope, receive, send)
        await wrapper(scope, receive, send)

        mock_ensure.assert_not_called()
        assert mock_app.call_count == 2


@pytest.mark.asyncio
async def test_lifespan_startup_complete():

    startup_received = False
    shutdown_received = False

    async def mock_app_handler(scope, receive, send):
        nonlocal startup_received, shutdown_received
        if scope["type"] == "lifespan":
            msg = await receive()
            assert msg["type"] == "lifespan.startup"
            startup_received = True
            await send({"type": "lifespan.startup.complete"})

            msg = await receive()
            assert msg["type"] == "lifespan.shutdown"
            shutdown_received = True
            await send({"type": "lifespan.shutdown.complete"})

    wrapper = FastMCPLifespanWrapper(mock_app_handler)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    await asyncio.sleep(0.01)

    assert wrapper.lifespan_started is True
    assert wrapper.startup_event.is_set()
    assert startup_received is True

    await wrapper.shutdown()
    assert shutdown_received is True


@pytest.mark.asyncio
async def test_lifespan_startup_failure():

    async def failing_app(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.failed", "message": "Initialization error"})

    wrapper = FastMCPLifespanWrapper(failing_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    await asyncio.sleep(0.01)

    assert wrapper.lifespan_task.done()
    with pytest.raises(RuntimeError, match="FastMCP lifespan startup failed"):
        await wrapper.lifespan_task


@pytest.mark.asyncio
async def test_ensure_lifespan_started_only_runs_once():

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            # Keep running
            await asyncio.Event().wait()

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()
        initial_task = wrapper.lifespan_task

        await wrapper._ensure_lifespan_started()

        assert wrapper.lifespan_task is initial_task
        assert mock_app.call_count == 1

    with contextlib.suppress(asyncio.CancelledError):

        if wrapper.lifespan_task and not wrapper.lifespan_task.done():
            wrapper.lifespan_task.cancel()

            await wrapper.lifespan_task

@pytest.mark.asyncio
async def test_lifespan_scope_structure():

    scope_received = None

    async def capture_scope_app(scope, receive, send):
        nonlocal scope_received
        if scope["type"] == "lifespan":
            scope_received = scope
            await receive()
            await send({"type": "lifespan.startup.complete"})
            # Keep running
            await asyncio.Event().wait()

    wrapper = FastMCPLifespanWrapper(capture_scope_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    await asyncio.sleep(0.01)

    assert scope_received is not None
    assert scope_received["type"] == "lifespan"
    assert "asgi" in scope_received
    assert scope_received["asgi"]["version"] == "3.0"
    assert "state" in scope_received

    with contextlib.suppress(asyncio.CancelledError):
        if wrapper.lifespan_task and not wrapper.lifespan_task.done():
            wrapper.lifespan_task.cancel()

            await wrapper.lifespan_task

@pytest.mark.asyncio
async def test_shutdown_completes_successfully():

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    assert wrapper.lifespan_task is not None
    assert not wrapper.lifespan_task.done()

    await wrapper.shutdown()

    assert wrapper.shutdown_event.is_set()
    assert wrapper.lifespan_task.done()


@pytest.mark.asyncio
async def test_shutdown_timeout_cancels_task():

    async def never_complete(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            # Never complete shutdown
            await asyncio.sleep(1000)

    mock_app = AsyncMock(side_effect=never_complete)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    assert wrapper.lifespan_task is not None

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        await wrapper.shutdown()

    assert wrapper.lifespan_task.cancelled()


@pytest.mark.asyncio
async def test_shutdown_handles_already_done_task():

    wrapper = FastMCPLifespanWrapper(Mock())

    async def completed_task():
        return True

    wrapper.lifespan_task = asyncio.create_task(completed_task())
    await wrapper.lifespan_task  # Wait for it to complete

    await wrapper.shutdown()


@pytest.mark.asyncio
async def test_shutdown_handles_no_task():

    wrapper = FastMCPLifespanWrapper(Mock())
    wrapper.lifespan_task = None

    await wrapper.shutdown()


@pytest.mark.asyncio
async def test_shutdown_multiple_times():

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            await receive()
            await send({"type": "lifespan.shutdown.complete"})

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    await wrapper.shutdown()
    assert wrapper.shutdown_event.is_set()

    await wrapper.shutdown()


@pytest.mark.asyncio
async def test_create_mcp_mount_initializes_wrapper():

    mock_router = Mock()
    mock_http_app = Mock()
    mock_router.http_app.return_value = mock_http_app

    mock_manager = Mock()
    mock_manager.router = mock_router

    with patch("asyncio.sleep", new=AsyncMock()):
        with patch("asyncio.create_task") as mock_create_task:

            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            wrapper = await create_mcp_mount_with_lifespan(mock_manager)

    assert isinstance(wrapper, FastMCPLifespanWrapper)
    assert wrapper.fastmcp_app is mock_http_app
    assert wrapper.lifespan_started is True
    mock_router.http_app.assert_called_once_with(path="/", transport="http")


@pytest.mark.asyncio
async def test_concurrent_request_handling():

    call_count = 0

    async def mock_app_handler(scope, receive, send):
        nonlocal call_count
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            await asyncio.Event().wait()
        else:
            call_count += 1
            await asyncio.sleep(0.01)

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    scope = {"type": "http", "path": "/"}
    receive = AsyncMock()
    send = AsyncMock()

    with patch("asyncio.sleep", new=AsyncMock()):

        await asyncio.gather(
            wrapper(scope, receive, send),
            wrapper(scope, receive, send),
            wrapper(scope, receive, send),
        )

    assert call_count == 3
    assert wrapper.lifespan_started is True

    with contextlib.suppress(asyncio.CancelledError):
        if wrapper.lifespan_task and not wrapper.lifespan_task.done():
            wrapper.lifespan_task.cancel()

            await wrapper.lifespan_task

@pytest.mark.asyncio
async def test_lifespan_receive_state_machine():

    receive_calls = []

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            msg1 = await receive()
            receive_calls.append(msg1)
            await send({"type": "lifespan.startup.complete"})

            msg2 = await receive()
            receive_calls.append(msg2)
            await send({"type": "lifespan.shutdown.complete"})

    wrapper = FastMCPLifespanWrapper(mock_app_handler)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    await asyncio.sleep(0.01)

    assert len(receive_calls) == 1
    assert receive_calls[0]["type"] == "lifespan.startup"
    assert wrapper.startup_event.is_set()

    await wrapper.shutdown()

    assert len(receive_calls) == 2
    assert receive_calls[1]["type"] == "lifespan.shutdown"


@pytest.mark.asyncio
async def test_lifespan_send_handles_all_message_types():

    sent_messages = []

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            sent_messages.append("startup.complete")

            await receive()
            await send({"type": "lifespan.shutdown.complete"})
            sent_messages.append("shutdown.complete")

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    await wrapper.shutdown()

    assert "startup.complete" in sent_messages
    assert "shutdown.complete" in sent_messages


@pytest.mark.asyncio
async def test_request_forwarding_preserves_scope_receive_send():

    forwarded_args = []

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            await asyncio.Event().wait()
        else:
            forwarded_args.append((scope, receive, send))

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    test_scope = {"type": "http", "path": "/test", "custom": "data"}
    test_receive = AsyncMock()
    test_send = AsyncMock()

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper(test_scope, test_receive, test_send)

    assert len(forwarded_args) == 1
    forwarded_scope, forwarded_receive, forwarded_send = forwarded_args[0]
    assert forwarded_scope is test_scope
    assert forwarded_receive is test_receive
    assert forwarded_send is test_send

    with contextlib.suppress(asyncio.CancelledError):
        if wrapper.lifespan_task and not wrapper.lifespan_task.done():
            wrapper.lifespan_task.cancel()

            await wrapper.lifespan_task


@pytest.mark.asyncio
async def test_shutdown_handles_cancelled_error():

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})

            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.sleep(1000)

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        await wrapper.shutdown()

    assert wrapper.shutdown_event.is_set()


@pytest.mark.asyncio
async def test_startup_delay_completes():

    sleep_called = False

    async def mock_sleep(duration):
        nonlocal sleep_called
        sleep_called = True
        assert duration == 0.1

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            await asyncio.Event().wait()

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    with patch("asyncio.sleep", new=mock_sleep):
        await wrapper._ensure_lifespan_started()

    assert sleep_called is True

    with contextlib.suppress(asyncio.CancelledError):
        if wrapper.lifespan_task and not wrapper.lifespan_task.done():
            wrapper.lifespan_task.cancel()

            await wrapper.lifespan_task


@pytest.mark.asyncio
async def test_lifespan_task_creation():

    async def mock_app_handler(scope, receive, send):
        if scope["type"] == "lifespan":
            await receive()
            await send({"type": "lifespan.startup.complete"})
            await asyncio.Event().wait()

    mock_app = AsyncMock(side_effect=mock_app_handler)
    wrapper = FastMCPLifespanWrapper(mock_app)

    assert wrapper.lifespan_task is None

    with patch("asyncio.sleep", new=AsyncMock()):
        await wrapper._ensure_lifespan_started()

    assert wrapper.lifespan_task is not None
    assert isinstance(wrapper.lifespan_task, asyncio.Task)
    assert not wrapper.lifespan_task.done()

    with contextlib.suppress(asyncio.CancelledError):
        if wrapper.lifespan_task and not wrapper.lifespan_task.done():
            wrapper.lifespan_task.cancel()

            await wrapper.lifespan_task