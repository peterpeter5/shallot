import inspect
import pytest
from shallot.ring import build_server, lifespan_handler
from unittest import mock
import asyncio
from test import awaitable_mock
from functools import partial


async def noop():
    return 

async def receive_none():
    return {'more_body': False}


async def send_none(x):
    print(x)


async def handler_identity(x):
    return {"status": 200, **x}


def test_ring_server_yields_function():
    server = build_server(lambda x: x)
    assert inspect.isfunction(server)


def test_server_func_returns_awaitable():
    server = build_server(lambda x: x)
    handler_func = server({"type": "http"}, receive_none, send_none)
    assert inspect.isawaitable(handler_func)


@pytest.mark.asyncio
async def test_server_coerces_header_list_into_dict():
    headers = [(b"a", b"asdff"), (b"ccccccccc"*1024, b"zu777/&!&/"), (b"double", b"123"), (b"double", b"asdf")]
    server = build_server(handler_identity)
    handler_func = partial(server, {"headers": headers, "type": "http"})
    result = await handler_func(receive_none, send_none)
    assert {"a": "asdff", "ccccccccc"*1024: "zu777/&!&/", "double": "123,asdf"} == result['headers']


@pytest.mark.asyncio
async def test_server_has_no_problems_with_empty_headers():
    server = build_server(handler_identity)
    handler_func = partial(server, {"type": "http"})
    result = await handler_func(receive_none, send_none)
    assert {} == result['headers']


@pytest.mark.asyncio
async def test_server_ignores_unknown_types_in_scope_and_simply_returns_None():
    server = build_server(handler_identity)
    receive_mock = mock.AsyncMock()
    send_mock = mock.AsyncMock()
    noop_result = await server({"type": "unknown"}, receive_mock, send_mock)
    
    assert noop_result is None, "Retrun value is not NONE"
    
    receive_unused = (not receive_mock.called) and (receive_mock.await_count == 0)
    assert receive_unused, "receive_function was used!"

    send_unused = (not send_mock.called) and (send_mock.await_count == 0)
    assert send_unused, "send_function was used!"


@pytest.mark.asyncio
async def test_server_raises_not_implemented_error_when_no_type_key_in_scope():
    server = build_server(handler_identity)
    with pytest.raises(NotImplementedError):
        await server({}, receive_none, send_none)


@pytest.mark.asyncio
@mock.patch("shallot.ring.lifespan_handler")
async def test_server_implements_a_handler_for_lifecycle_protocol(lifespan_handler):

    server = build_server(handler_identity)
    _ = await server({"type": "lifespan"}, receive_none, send_none)
    lifespan_handler.assert_called()
    lifespan_handler.assert_awaited()


@pytest.mark.asyncio
@mock.patch("shallot.ring._default_on_start")
async def test_lifespan_default_callbacks_start_are_used_when_nothing_is_provided(mocked_on_start):
    
    called_at_least_once = False
    async def receive_start_up():
        nonlocal called_at_least_once

        if not called_at_least_once:
            called_at_least_once = True

            return {"type": "lifespan.startup"}
        else:
            await asyncio.sleep(10)
    
    receive_mock = mock.AsyncMock(side_effect=receive_start_up)
    send_mock = mock.AsyncMock()
    
    server = build_server(handler_identity, on_start=mocked_on_start)
    
    from asyncio import TimeoutError as AsyncTimeoutError

    with pytest.raises(AsyncTimeoutError):
        lifecycle_handler = server({"type": "lifespan"}, receive_mock, send_mock)
        await asyncio.wait_for(asyncio.ensure_future(lifecycle_handler), timeout=0.3)

    mocked_on_start.assert_called_once()
    mocked_on_start.assert_awaited_once()
    assert send_mock.call_args_list == [mock.call({"type": "lifespan.startup.complete"})]


@pytest.mark.asyncio
@mock.patch("shallot.ring._default_on_stop")
async def test_lifespan_default_callbacks_stops_are_used_when_nothing_is_provided(mocked_on_stop):
    
    async def receive_shutdown():
        return {"type": "lifespan.shutdown"}
        
    
    server = build_server(handler_identity, on_stop=mocked_on_stop)

    receive_mock = mock.AsyncMock(side_effect=receive_shutdown)
    send_mock = mock.AsyncMock()

    _ = await server({"type": "lifespan"}, receive_mock, send_mock)
   
    mocked_on_stop.assert_called_once()
    mocked_on_stop.assert_awaited_once()

    assert send_mock.call_args_list == [mock.call({"type": "lifespan.shutdown.complete"})]


@pytest.mark.asyncio
async def test_lifespan_startup_failed_is_used_when_start_up_func_raises():
    
    class TestCaseException(Exception): pass

    async def receive_start_up():
        return {"type": "lifespan.startup"}
        
    async def raise_on_startup(context):
        raise TestCaseException("On startup something bad happend!")
    

    receive_mock = mock.AsyncMock(side_effect=receive_start_up)
    send_mock = mock.AsyncMock()
    server = build_server(handler_identity, on_start=raise_on_startup)
    
    with pytest.raises(TestCaseException):
        await server({"type": "lifespan"}, receive_mock, send_mock)

    start_up_failed_event = {"type": "lifespan.startup.failed", "message": "On startup something bad happend!"}
    assert send_mock.call_args_list == [mock.call(start_up_failed_event)]


@pytest.mark.asyncio
async def test_lifespan_shutdown_failed_is_used_when_start_down_func_raises():
    class TestCaseException(Exception): pass

    async def raise_on_shutdown(context):
        raise TestCaseException("On shutdown it happend!")
    
    async def receive_shutdown():
        return {"type": "lifespan.shutdown"}
        
    receive_mock = mock.AsyncMock(side_effect=receive_shutdown)
    send_mock = mock.AsyncMock()
    
    server = build_server(handler_identity, on_stop=raise_on_shutdown)

    with pytest.raises(Exception):
        await server({"type": "lifespan"}, receive_mock, send_mock)

    shutdown_failed_event = {"type": "lifespan.shutdown.failed", "message": "On shutdown it happend!"}
    assert send_mock.call_args_list == [mock.call(shutdown_failed_event)]



@pytest.mark.asyncio
async def test_every_request_has_an_empty_config_if_startup_does_nothing():
    server = build_server(handler_identity)
    result = await server({"type": "http"}, receive_none, send_none)
    assert result["config"] == {}


@pytest.mark.asyncio
async def test_websockets_have_an_empty_config_if_startup_does_nothing():
    server = build_server(handler_identity)
    result = await server({"type": "websocket"}, receive_none, send_none)
    assert result["config"] == {}


@pytest.mark.asyncio
async def test_requests_are_stacked_when_startup_is_not_completed():
    server = build_server(handler_identity)
    lifespan_channel = asyncio.Queue()
    application_events = asyncio.Queue()
    request_channel = asyncio.Queue()
    startup = server({"type": "lifespan"}, lifespan_channel.get, application_events.put)
    http = server({"type": "http"}, request_channel.get, application_events.put)

    
    http_f = asyncio.ensure_future(http)
    startup_f = asyncio.ensure_future(startup)
    assert not http_f.done()
    assert not startup_f.done()
    
    await request_channel.put({"type": "http", "more_body": False})
    assert not http_f.done()

    await lifespan_channel.put({"type": "lifespan.startup"})

    await asyncio.sleep(0.01)
    assert not startup_f.done()

    assert http_f.done()

    acc = []
    for _ in range(application_events.qsize()):
        acc.append(await application_events.get())
    

    assert acc == [
        {"type": "lifespan.startup.complete"}, 
        {'type': 'http.response.start', 'status': 200, 'headers': []},
        {'type': 'http.response.body', 'body': b'', 'more_body': False}
    ]
    startup_f.cancel()


     