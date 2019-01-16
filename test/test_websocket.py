import pytest
from shallot import build_server
from shallot.websocket import _build_receiver, WSDisconnect


@pytest.fixture
def disable_conftest():
    import sys
    del sys._pytest_
    yield 
    sys._pytest_ = True


async def receive_raise():
    raise NotImplementedError("you should not read from here!")


async def send_none(x):
    pass


async def _handle_identity(request):
    return {"status": 0, **request}


async def raw_asgi_handler(receive, send):
    pass


async def raw_asgi_wrapper(scope):
    return raw_asgi_handler


def ws_receive(data):
    key = "bytes" if isinstance(data, bytes) else "text"
    return {"type": "websocket.receive", key: data}


def receive_func_from_coll(coll):
    async def _gen():
        for item in coll:
            yield item
    gen = _gen()
    
    return gen.__anext__



@pytest.mark.asyncio
async def test_app_handler_adds_WS_as_method_for_websockets():
    app = build_server(_handle_identity)
    response = await (app({"type": "websocket"})(receive_raise, send_none))
    assert "method" in response
    assert response["method"] == "WS"


@pytest.mark.asyncio
async def test_app_handler_exposes_asgi_interface_for_ws():
    app = build_server(raw_asgi_wrapper)
    response = await (app({"type": "websocket"})(receive_raise, send_none))
    assert response is raw_asgi_handler


@pytest.mark.asyncio
async def test_receiver_returns_only_data():
    expected_result = ["a", b"b", "", b""]
    receive_msgs = map(ws_receive, expected_result)
    result = [
        a 
        async for a in _build_receiver(
            receive_func_from_coll(receive_msgs))
    ]
    assert expected_result == result


@pytest.mark.asyncio
async def test_receiver_raises_all_errors(disable_conftest):
    async def raise_stop_iteration():
        raise StopIteration()

    async def raise_async_stop_iteration():
        raise StopAsyncIteration()

    async def raise_base_exception():
        raise BaseException()
    
    async def raise_value_error():
        raise ValueError()

    
    with pytest.raises(RuntimeError):
        receiver = _build_receiver(raise_async_stop_iteration)
        await receiver.__anext__()

    with pytest.raises(RuntimeError):
        [_ async for _ in _build_receiver(raise_stop_iteration)]


    with pytest.raises(BaseException) as base_exp_info:
        [_ async for _ in _build_receiver(raise_base_exception)]
    assert base_exp_info.type is BaseException

    with pytest.raises(ValueError):
        [_ async for _ in _build_receiver(raise_value_error)]
    

@pytest.mark.asyncio
async def test_receiver_raises_ws_disconnect_on_message():
    message_stream = [
        {"type": "websocket.receive", "text": "hello"},
        {"type": "websocket.disconnect"}
    ]
    receiver = _build_receiver(receive_func_from_coll(message_stream))
    with pytest.raises(WSDisconnect):
        msg = await receiver.__anext__()
        assert msg == "hello"
        await receiver.__anext__()


@pytest.mark.asyncio
async def test_receiver_raises_ws_connection_error_on_unsupported_message():
    message_stream = [
        {"type": "websocket.connect",},
        {"type": "websocket.disconnect"}
    ]
    receiver = _build_receiver(receive_func_from_coll(message_stream))
    with pytest.raises(ConnectionError):
        msg = await receiver.__anext__()


@pytest.mark.asyncio
async def test_gen_strategy(parameter_list):
    pass