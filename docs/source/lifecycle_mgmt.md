# Start-Up / Tear-Down / Configuration

`shallot` provides a way to register functions, which get called when the webserver has started or when it is about to stop.
This functions can be used for setting-up your application. Your `on_start` - function will be called when the server has started,
but before it actually accepts connections. Even more, the asyncio-loop has been set by the server and can now been used by 
your application for starting background-tasks or initialize other code like database-connections.

To register your `on_start` - function, create an async-function with the following signature:

```python
async def on_start(context):
    return {"db": db_connnection, "anything_else": ...}

```

You must provide an async-function, that accepts one parameter. Your `on_start`- function will be called with the current scope of the 
lifespan-event (a `dict`), that is provided by the server. (see [asgi-specification](https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-protocol)). The data you return, will be appended to every request
and is accessible under the key `config`

```python
async def http_handler(request):
    db = request["config"]["db"]
    result = db.query()
    ...

```

If you want to be notified when the server is going to shut down, then you can provide an `on_stop` - function with the same signature
as `on_start`:

```python
async def on_stop(context):
    ...
    db_connnection.close()
    # log the server-shutdown
```

When `on_stop` is called, then the server has already stopped accepting requests and just waits on you to tear-down your application.

Both functions `on_start` and `on_stop` are registered via `build_server`

```python
server = build_server(handler, on_start=on_start, on_stop=on_stop)

```






