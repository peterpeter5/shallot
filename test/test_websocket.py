import pytest
from shallot import build_server, websocket
from shallot.websocket import _build_receiver, WSDisconnect, _ws_async_generator_client
from shallot.response import ws_send, ws_close
from unittest.mock import Mock, call
from test import awaitable_mock


@pytest.fixture
def disable_conftest():
    import sys
    del sys._pytest_shallot_
    yield 
    sys._pytest_shallot_ = True


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
    mock = Mock()
    mock.side_effect = list(coll) + [StopAsyncIteration]
    return awaitable_mock(mock)


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
        async for a in _build_receiver(receive_func_from_coll(receive_msgs))
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
        _ = await receiver.__anext__()


@pytest.mark.asyncio
async def test_ws_servers_that_provide_missing_data_in_receiver_yield_conenction_error():
    receiver =  _build_receiver(receive_func_from_coll(
        [
            {"type": "websocket.receive",},
        ]))
    with pytest.raises(ConnectionError):
        _ = await receiver.__anext__()



@pytest.mark.asyncio
async def test_gen_strategy_will_send_every_message_that_gets_yielded():
    async def ws_echo_handler(scope, receiver):
        async for msg in receiver:
            yield ws_receive(msg)

    sender = Mock().send
    async_sender = awaitable_mock(sender)
    fake_messages = list(map(ws_receive, ["a", b"", "1", b"2"]))
    receiver = receive_func_from_coll(fake_messages)
    await _ws_async_generator_client(
        ws_echo_handler,
        {},
        tuple(),
        receiver,
        async_sender
        )
    sender.assert_has_calls(list(map(call, fake_messages)))


@pytest.mark.asyncio
async def test_ws_handler_can_be_non_generators():
    async def ws_just_return_first_message(scope, receiver):
        async for msg in receiver:
            return ws_receive(msg)

    async def ws_return_nothing(scope, receiver):
        pass


    sender = Mock().send
    async_sender = awaitable_mock(sender)
    fake_messages = list(map(ws_receive, ["a", b"", "1", b"2"]))
    receiver = receive_func_from_coll(fake_messages)
    await _ws_async_generator_client(
        ws_just_return_first_message,
        {},
        tuple(),
        receiver,
        async_sender
    )
    
    assert sender.mock_calls == [call(fake_messages[0]), call(ws_close())]

    sender.reset_mock()
    await _ws_async_generator_client(
        ws_return_nothing,
        {},
        tuple(),
        receiver,
        async_sender
    )

    assert sender.mock_calls == [call(ws_close())]



@pytest.mark.asyncio
async def test_close_gets_automatically_sended_when_client_stops_yielding_messages():
    async def ws_close_immediately(scope, receiver):
        yield ws_send("adf")

    sender = Mock().send
    async_sender = awaitable_mock(sender)
    fake_messages = list(map(ws_receive, ["a"]))
    receiver = receive_func_from_coll(fake_messages)
    await _ws_async_generator_client(
        ws_close_immediately,
        {},
        tuple(),
        receiver,
        async_sender
        )
    assert sender.call_args_list == list(map(call, [ws_send("adf"), {"type": "websocket.close", "code": 1000}]))


@pytest.mark.asyncio
async def test_close_will_only_get_once_when_client_yields_a_close():
    async def ws_close_actively(scope, receiver):
        yield ws_close(2000)

    sender = Mock().send
    async_sender = awaitable_mock(sender)
    fake_messages = list(map(ws_receive, ["a"]))
    receiver = receive_func_from_coll(fake_messages)
    await _ws_async_generator_client(
        ws_close_actively,
        {},
        tuple(),
        receiver,
        async_sender
        )
    assert sender.call_args_list == list(map(call, [{"type": "websocket.close", "code": 2000}]))


@websocket
async def send_2_messages(scope, receive):
    for index in range(2):
        yield ws_send(str(index))


async def close_immediatly(scope, receive):
    yield ws_close()


async def disconnect_immediatly(scope, receive):
    raise WSDisconnect("sorry! wrong number!")
    yield  # unreacheable but makes the function an interator


async def _on_dis_ignore(scope):
    pass


@websocket(on_disconnect=_on_dis_ignore)
async def raise_ws_disconnect_simulate_client_disconnect_with_custom_disconnect_handler(scope, receive):
    yield ws_send("this is good")
    raise WSDisconnect("Good Bye")


@websocket()
async def raise_ws_disconnect_simulate_client_disconnect(scope, receive):
    yield ws_send("this is good")
    raise WSDisconnect("Good Bye")


async def run_ws_handler_with_messages(handler, messages, scope_type="websocket"):
    scope = {"type": scope_type}
    sender = Mock().send
    async_sender = awaitable_mock(sender)
    receiver = receive_func_from_coll(messages)
    initialized_handler = await handler(scope)
    await initialized_handler(receiver, async_sender)
    return sender.call_args_list

@pytest.mark.asyncio
async def test_ws_handler_raises_error_when_handshake_msg_is_missing():

    with pytest.raises(ConnectionError):
        await run_ws_handler_with_messages(
            send_2_messages,
            list(map(ws_receive, ["1"]))
        )

@pytest.mark.asyncio
async def test_ws_handler_raises_error_when_called_outside_ws_scope():
    with pytest.raises(ConnectionError):
        _ = await run_ws_handler_with_messages(
            send_2_messages,
            list(map(ws_receive, ["1"])),
            scope_type="http"
        )


@pytest.mark.asyncio
async def test_ws_handler_raising_ws_disconnect_does_not_leak_outside_custom():

    sended_messages = await run_ws_handler_with_messages(
        raise_ws_disconnect_simulate_client_disconnect_with_custom_disconnect_handler,
        [
            {"type": "websocket.connect"},
            ws_receive("mb:lisa"),
        ],
    )
    assert sended_messages == [call({"type": "websocket.accept"}), call(ws_send("this is good"))] 


@pytest.mark.asyncio
async def test_ws_handler_raising_ws_disconnect_does_not_leak_outside():

    sended_messages = await run_ws_handler_with_messages(
        raise_ws_disconnect_simulate_client_disconnect,
        [
            {"type": "websocket.connect"},
            ws_receive("mb:lisa"),
        ],
    )
    assert sended_messages == [call({"type": "websocket.accept"}), call(ws_send("this is good"))] 


@pytest.mark.asyncio
async def test_ws_handler_default_will_accept_every_connect():
    sended_messages = await run_ws_handler_with_messages(
        websocket(close_immediatly),
        [{"type": "websocket.connect"}],
        scope_type="websocket"
    )
    assert sended_messages == [call({"type": "websocket.accept"}), call(ws_close())]


@pytest.mark.asyncio
async def test_ws_handler_can_have_custom_on_conenct():
    async def never_accept_connect(scope):
        return ws_close()

    sended_messages = await run_ws_handler_with_messages(
        websocket(close_immediatly, on_connect=never_accept_connect),
        [{"type": "websocket.connect"}],
        scope_type="websocket"
    )
    assert sended_messages == [call(ws_close())]


@pytest.mark.asyncio
async def test_ws_handler_can_have_custom_on_disconnect():
    disconnect = Mock()

    _ = await run_ws_handler_with_messages(
        websocket(disconnect_immediatly, on_disconnect=awaitable_mock(disconnect)),
        [{"type": "websocket.connect"}],
        scope_type="websocket"
    )
    disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_ws_handler_can_have_custom_on_close():
    close = Mock()

    _ = await run_ws_handler_with_messages(
        websocket(close_immediatly, on_close=awaitable_mock(close)),
        [{"type": "websocket.connect"}],
        scope_type="websocket"
    )
    close.assert_called_once()
