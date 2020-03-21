# Websockets

websockets are (potentially) long-living 2-way connections. Therefor websocket-handlers are different to 
"normal" http-handlers. Nevertheless `shallot` tries to apply the same ideas (data-driven) to this kind
of process. A potentially never-ending process in python can be modeled as generator. That's exactly how
it is done for websockets.

```python
@websocket
async def handle_ws_echo(scope, receiver):
    async for message in receiver:
        yield {"text": f"@ECHO: {message}", "type": "websocket.send"}
        if message == "exit":
            yield ws_send("bybye")
            yield ws_close(1001)
```

The above example shows a simple echo-server implementation. This function can be used as a normal handler with all other
`middlewares`, especially with `routing`. 
The first argument `scope` represents all information from the opening-handshake-request and all `middlewares` enhancing it. The
second argument `receiver` is an async-generator which yields all data from the client. The data can be `str` or `bytes` depending on your clients choice. 

To send data to your client you must yield it from your handler. Your data must be a `dict` with a key `text` or `bytes` and the type
`websocket.send`. You can use the convenience-function `ws_send` to construct this `dict`. You do not have to close your websocket via the function `ws_close`. By default `shallot` will close the websocket when you stop yielding messages. The default return-code is 1000. However, if you want to close the websocket with
and alternative return-code, you can use the `ws_close` function to construct a `dict` with the corresponding attributes. **note** your connection will be closed immediately and you can not send any data after yielding `ws_close`. 

When your client closes the websocket, a dedicated `on_disconnect` - handler will be called. The same is true, when the connection gets closed (either by the server or by the client disconnect). 

**note** `on_disconnect` will only be called when client closes the socket, `on_close` will be called anyway when the socket is closed by server or client  

```python 
from shallot import websocket


async def my_disconnect(scope):
    print("-> Client Disconnected!")


async def my_close(scope):
    print("--> The connection has been closed! Either by the server or by the client")


@websocket(on_disconnect=standard_disconnect)
async def handle_ws_echo(scope, receiver):
    async for message in receiver:
        yield ws_send(f"@ECHO: {message}")
        

```

In the example above, when a client disconnects you should see the following output:

```
-> Client Disconnected!
--> The connection has been closed! Either by the server or by the client

```

By default, a websocket-handler accepts every connection. You can customize this behavior by providing a dedicated `on_connect` - function. The `on_connect` gets a scope and **must** return a `dict` either accepting the connection (with optional `subprotocol`) or closing it immediately.

```python
async def connection_accept(scope):
    if something():
        return ws_accept(subprotocol="sub-123")  # == {"type": "websocket.accept", "subprotocol": "sub-123"}
    else:
        return ws_close()


@websocket(on_connect=connection_accept)
async def handle_ws_echo(scope, receiver):
    async for message in receiver:
        yield ws_send(f"@ECHO: {message}")
```

The function `connection_accept` accepts or declines the connection attempt by the client based on the result of `something()`. The subprotocol is an optional parameter.    