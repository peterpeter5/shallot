import asyncio
from functools import partial
from .response import ws_close
import sys
import contextlib
from collections.abc import AsyncGenerator


class WSDisconnect(Exception):
    pass


@contextlib.contextmanager
def _in_maybe_unittest():
    try:
        yield
    except (StopAsyncIteration, StopIteration):  # Thank you: PEP479!
        if hasattr(sys, "_pytest_shallot_"):
            return
        else:
            raise


async def _build_receiver(receive):
    with _in_maybe_unittest():  # FIXME remove this once a better unittest-concept comes to mind
        while True:

            message = await receive()

            if message["type"] == "websocket.receive":
                data = message.get("text")
                data = message.get("bytes") if data is None else data

                if data is None:
                    raise ConnectionError(
                        "Server is not ASGI-compliant." "websocket.receive neither contains 'text' nor 'bytes' - data!"
                    )

                yield data

            elif message["type"] == "websocket.disconnect":
                raise WSDisconnect()
            else:
                raise ConnectionError(f"unexpected-message-type: {message['type']}")


async def _default_on_connect(scope):
    return {"type": "websocket.accept"}


async def _default_on_disconnect(scope):
    pass


async def _default_on_close(scope):
    pass


async def _ensure_generator(afunc):
    result = await afunc
    if result:
        yield result
    else:
        yield {"type": "websocket.close", "code": 1000}


async def _ws_async_generator_client(func, scope, extras, receive, send):

    receiver = _build_receiver(receive)
    client = func(scope, receiver, *extras)
    if not isinstance(client, AsyncGenerator):
        client = _ensure_generator(client)

    closed = False
    async for client_message in client:
        if client_message["type"] == "websocket.close":
            closed = True
        await send(client_message)
        if closed:
            break

    if not closed:
        await send(ws_close())


async def _ws_handler(scope, extras, receive, send, func, on_connect, on_disconnect, on_close):
    if scope["type"] != "websocket":
        raise ConnectionError(f"received a {scope['type']}-request on a websocket-handler")

    connect = await receive()
    if connect["type"] != "websocket.connect":
        raise ConnectionError(f"Websockets first message wasn't connect! Instead: {connect}")

    _handle_on_connect = on_connect or _default_on_connect
    result = await _handle_on_connect(scope)
    await send(result)
    if result["type"] == "websocket.close":
        return result

    _handle_disconnect = on_disconnect or _default_on_disconnect
    try:
        await _ws_async_generator_client(func, scope, extras, receive, send)
    except WSDisconnect:
        await _handle_disconnect(scope)

    try:  # drain an close the receiver
        with _in_maybe_unittest():
            await asyncio.wait_for(receive(), timeout=1)
    except asyncio.TimeoutError:
        pass

    _handle_on_close = on_close or _default_on_close
    await _handle_on_close(scope)


def websocket(func=None, on_connect=None, on_disconnect=None, on_close=None):
    async def handle_scope(*args, func=None):
        scope, *extras = args
        return partial(
            _ws_handler,
            scope,
            extras,
            func=func,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            on_close=on_close,
        )

    def wrap_handler(handler):
        return partial(handle_scope, func=handler)

    if func is None:
        return wrap_handler
    else:
        return partial(handle_scope, func=func)
