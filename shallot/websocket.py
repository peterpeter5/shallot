import asyncio
from functools import partial
from .response import ws_close
import sys

class WSDisconnect(Exception): pass


async def _build_receiver(receive):

    while True:
        try:
            message = await receive()
        except (StopAsyncIteration, StopAsyncIteration):  # Thank you: PEP479!
            if hasattr(sys, "_pytest_"):
                return
            else:
                raise
        except Exception:
            raise
        
        if message["type"] == "websocket.receive": 
            data = message.get("text")
            data = message.get("bytes") if data is None else data
                
            if data is None:
                raise ConnectionError("Server is not ASGI-compliant."
                    "websocket.receive neither contains 'text' nor 'bytes' - data!")

            yield data
        
        elif message["type"] == "websocket.disconnect":
            raise WSDisconnect()
        else:
            raise ConnectionError(f"unexpected-message-type: {message['type']}")


async def _default_on_connect(scope):
    return {"type": "websocket.accept"}


async def _default_on_disconnect():
    pass


async def _ws_async_generator_client(func, scope, extras, receive, send):
    closed = False

    receiver = _build_receiver(receive)
    client = func(scope, receiver, *extras)
    async for client_message in client:
        if client_message["type"] == "websocket.close":
            closed = True
        await send(client_message)
    
    if not closed:
        await send(ws_close())
    


def websocket(func, on_connect=None, on_disconnect=None):

    
    async def ws_handler(scope, extras, receive, send):
        if  scope["type"] != "websocket":
            raise ConnectionError(f"received a {scope['type']}-request on a websocket-handler")

        connect = await receive()
        if connect["type"] != "websocket.connect":
            raise ConnectionError("Websockets first message wasn't connect")
        
        _handle_on_connect = on_connect or _default_on_connect
        result = await _handle_on_connect(scope)
        await send(result)
        if result["type"] == "websocket.close":
            return result

        try:
            await _ws_async_generator_client(func, scope, extras, receive, send)
        except WSDisconnect:
            pass

        done, _ = await asyncio.wait([receive()], timeout=1)
        _handle_disconnect = on_disconnect or _default_on_disconnect
        await _handle_disconnect()
        

    async def handle_scope(*args):
        scope, *extras = args
        return partial(ws_handler, scope, extras) 
    
    return handle_scope
