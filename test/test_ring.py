import inspect
import pytest
from shallot.ring import build_server, noop, lifespan_handler
from unittest import mock
import asyncio
from test import awaitable_mock
from functools import partial


async def receive_none():
    return {'more_body': False}


async def send_none(x):
    print(x)


async def handler_identity(x):
    return {"status": 200, **x}


def test_ring_server_yields_function():
    server = build_server(lambda x: x)
    assert inspect.isfunction(server)


def test_server_func_returns_handler_func_or_partial_for_request():
    server = build_server(lambda x: x)
    handler_func = server({"type": "http"})
    assert inspect.isfunction(handler_func) or isinstance(handler_func, partial)


@pytest.mark.asyncio
async def test_server_coerces_header_list_into_dict():
    headers = [(b"a", b"asdff"), (b"ccccccccc"*1024, b"zu777/&!&/"), (b"double", b"123"), (b"double", b"asdf")]
    server = build_server(handler_identity)
    handler_func = server({"headers": headers, "type": "http"})
    result = await handler_func(receive_none, send_none)
    assert {"a": "asdff", "ccccccccc"*1024: "zu777/&!&/", "double": "123,asdf"} == result['headers']


@pytest.mark.asyncio
async def test_server_has_no_problems_with_empty_headers():
    server = build_server(handler_identity)
    handler_func = server({"type": "http"})
    result = await handler_func(receive_none, send_none)
    assert {} == result['headers']


@pytest.mark.asyncio
async def test_server_ignores_unknown_types_in_scope():
    server = build_server(handler_identity)
    lifecycle_handler = server({"type": "unknown"})
    assert lifecycle_handler.__name__ == noop.__name__ 


@pytest.mark.asyncio
async def test_server_raises_not_implemented_error_when_no_type_key_in_scope():
    server = build_server(handler_identity)
    with pytest.raises(NotImplementedError):
        server({})


@pytest.mark.asyncio
async def test_server_implements_a_handler_for_lifecycle_protocol():
    server = build_server(handler_identity)
    lifecycle_handler = server({"type": "lifespan"})
    assert lifecycle_handler.func.__name__ == lifespan_handler.__name__ 


@pytest.mark.asyncio
@mock.patch("shallot.ring._default_on_start")
async def test_lifespan_default_callbacks_start_are_used_when_nothing_is_provided(mocked_on_start):
    send_data = []
    
    called_once = False
    async def receive_start_up():
        nonlocal called_once 

        if not called_once:
            called_once = True
            return {"type": "lifespan.startup"}
        else:
            await asyncio.sleep(10)

    async def send_mocked(arg):
        send_data.append(arg)
    
    server = build_server(handler_identity, on_start=awaitable_mock(mocked_on_start))
    lifecycle_handler = server({"type": "lifespan"})
    from concurrent.futures import TimeoutError
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(asyncio.ensure_future(lifecycle_handler(receive_start_up, send_mocked)), timeout=0.3)

    mocked_on_start.assert_called_once()
    assert send_data == [{"type": "lifespan.startup.complete"}]


@pytest.mark.asyncio
@mock.patch("shallot.ring._default_on_stop")
async def test_lifespan_default_callbacks_stops_are_used_when_nothing_is_provided(mocked_on_stop):
    send_data = []
    
    async def receive_shutdown():
        return {"type": "lifespan.shutdown"}
        
    async def send_mocked(arg):
        send_data.append(arg)
    
    server = build_server(handler_identity, on_stop=awaitable_mock(mocked_on_stop))
    lifecycle_handler = server({"type": "lifespan"})
   
    await lifecycle_handler(receive_shutdown, send_mocked)

    mocked_on_stop.assert_called_once()
    assert send_data == [{"type": "lifespan.shutdown.complete"}]


@pytest.mark.asyncio
async def test_lifespan_startup_failed_is_used_when_start_up_func_raises():
    send_data = []
    
    async def receive_start_up():
        return {"type": "lifespan.startup"}
        
    async def send_mocked(arg):
        send_data.append(arg)

    async def raise_on_startup(context):
        raise Exception("On startup something bad happend!")
    
    server = build_server(handler_identity, on_start=raise_on_startup)
    lifecycle_handler = server({"type": "lifespan"})
    with pytest.raises(Exception):
        await lifecycle_handler(receive_start_up, send_mocked)

    assert send_data == [{"type": "lifespan.startup.failed", "message": "On startup something bad happend!"}]


@pytest.mark.asyncio
async def test_lifespan_shutdown_failed_is_used_when_start_down_func_raises():
    send_data = []
    
    async def receive_shutdown():
        return {"type": "lifespan.shutdown"}
        
    async def send_mocked(arg):
        send_data.append(arg)

    async def raise_on_shutdown(context):
        raise Exception("On shutdown it happend!")
    
    server = build_server(handler_identity, on_stop=raise_on_shutdown)
    lifecycle_handler = server({"type": "lifespan"})
    with pytest.raises(Exception):
        await lifecycle_handler(receive_shutdown, send_mocked)

    assert send_data == [{"type": "lifespan.shutdown.failed", "message": "On shutdown it happend!"}]


@pytest.mark.asyncio
async def test_every_request_has_an_empty_config_if_startup_does_nothing():
    server = build_server(handler_identity)
    http_handler = server({"type": "http"})
    result = await http_handler(receive_none, send_none)
    assert result["config"] == {}


@pytest.mark.asyncio
async def test_websockets_have_an_empty_config_if_startup_does_nothing():
    server = build_server(handler_identity)
    ws_handler = server({"type": "websocket"})
    result = await ws_handler(receive_none, send_none)
    assert result["config"] == {}


@pytest.mark.asyncio
async def test_requests_are_stacked_when_startup_is_not_completed():
    server = build_server(handler_identity)
    lifespan_channel = asyncio.Queue()
    application_events = asyncio.Queue()
    request_channel = asyncio.Queue()
    startup_handler = server({"type": "lifespan"})
    http_handler = server({"type": "http"})

    http = http_handler(request_channel.get, application_events.put)
    startup = startup_handler(lifespan_channel.get, application_events.put)
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


     