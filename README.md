# shallot - a plugable "webframework"
[![Documentation Status](https://readthedocs.org/projects/shallot/badge/?version=latest)](https://shallot.readthedocs.io/en/latest/?badge=latest)
![](https://github.com/peterpeter5/shallot/workflows/Python%20package/badge.svg)
[![PyPI version](https://badge.fury.io/py/shallot.svg)](https://pypi.org/project/shallot/)

## What is a shallot?

It is a small onion. It has only small and few layers. When you use it (cut it for cooking), it does not make 
you cry (that much).

The above description of the vegetable, is a good mission-statement for what `shallot` (the [micro-] "webframework") tries to be. 

`shallot` is a small layer on top of an ASGI - compatible server, like: uvicorn, hypercorn, ... It is haveliy inspired 
by [ring](https://github.com/ring-clojure/ring). The main difference to other webframeworks is, that `shallot` is easily plug able and extensible. Every component can be switched and new features can be added without touching `shallot`s source-code. That is accomplished by using middlewares for nearly every functionality in `shallot`.

`shallot` tries hard, to provide a *simple* API. For that, only standard-types and functions (and one decorator) are used. The goal is, that a user can
freely choose her / his tools for testing, documentation and so on. Another benefit, extending `shallot`s functionality requires you to understand the
middleware-concept and that is all. No class-hierarchies or plugin-frameworks are needed.    

## Architecture

`shallot` is an [ASGI](https://asgi.readthedocs.io/en/latest/index.html) - compatible webframework. 

### Basic-Concepts

`shallot` models a http-request-response-cycle as single function call. It treats `request` and `response` as `dict`s. The request get passed to a `handler` (which itself can be "middleware-decorated") and the `handler` produces a response.
Basically `shallot` works like this:
1. take the ASGI [connection-scope](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope) (`dict`)
2. read the body of the request and attach the body (`bytes`) to scope-dict 
3. pass the request-`dict` (scope + attached body) to a user-defined function (called `handler`)
4. the result (`response`) of a handler has to be a `dict`. The response must at least provide a `status`-key with an integer. If provided a `body`-key for the response is provided, than the value must be of type `bytes` and to will be transferred to the client. 

### data-flow

```
+----------+           +----------+             +------------+
|          |           |          |             |            |
|          +-----------> request  +-------------> middlewares+-----------+
|          |           |          |             | (enter)    |           |
|          |           +----------+             +------------+           |
|    A     |                                                             |
|    S     |                                                             |
|    G     |                                                             |
|    I     |                                                             |
|          |                                                   +---------v--------+
|    |     |                                                   |                  |
|          |                                                   |    handler       |
|    S     |                                                   |                  |
|    E     |                                                   +---------+--------+
|    R     |                                                             |
|    V     |                                                             |
|    E     |                                                             |
|    R     |           +----------+             +------------+           |
|          |           |          |             |            |           |
|          <-----------+ response <-------------+ middlewares<-----------+
|          |           |          |             | (leave)    |
+----------+           +----------+             +------------+
```

### request

The `request` is always the first argument that gets passed to your `handler`-function. It is of type `dict`. It has basically the same content as the [ASGI-connection-scope](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope). 

A request will at least have the following structure:

- `type`: http [string]
- `method`: the http-verb in uppercase (for example: "GET", "PUT", "POST", ...) [`string`]
- `headers`: a `dict` with all header-names as `keys` and the corresponding-values as `values` of the dict.
- `body`: The body of the http-request as `bytes`. `shallot` always read the entire body and then calls the `handler`-function. [`bytes`] 

- **note**: many fields are missing! please refer to the documentation  

### response

The `response` is the result of the function-call to the handler (with the `request` as first argument). The `response` has to be a `dict`. The reponse must have the following structure:

- `status`: the http-return-code [`int`]
- `body` [optional]: the body of the http-response [`bytes`]
- `headers` [optional]: the http-response-headers to be used. The value is a `dict` (for example: `{"header1-name": "header1-value", ...}`)
- `stream` [optional]: this must be an `async-iterable` yielding `bytes`. When the `response` contains a key named `stream`, than `shallot` will consume the `iterable` and will stream the provided data to the client. This is specially useful for large response-bodies.

### handler

`shallot` assembles a request-dict and calls a user-provided handler. A `handler` is an async-function that takes a request and returns a response (`dict`).  

```python
async def handler(request):
    return {"status": 200}
```

### middleware

Most of `shallot`s  functionality is implemented via middlewares. That makes it possible to easily extend, configure or change `shallot`s behaviour. In fact: if you don't like the implementation of a certain middleware, just write your own and use it instead (or better: enhance `shallot` via PR)!

The general functionality of a middleware is, that it wraps a handler-function-call. Middlewares are designed that way, that they can be composed / chained together. So for a middleware-chain with 3 different middlewares, a call chain might look like:

```
|-> middleware 1 (enter)
    |-> middleware 2 (enter)
        |-> middleware 3 (enter)
            |-> handler (execute)
        |<- middleware 3 (leave)
    |<- middleware 2 (leave)
|<- middleware 1 (leave)
```

A good analogy for a middleware is a python-decorator. A decorator wraps a function and returns another function to provide extended functionality.


### application

the minimal deployable thing, one can build is this:

```python
async def minimal(request):
    """
    answer EVERY request with 200 and NO body 
    """
    return {"status": 200}

server = build_server(minimal)

if __name__ == "__main__":
    import uvicorn  # shallot is not tied to uvicorn, its just fast
    uvicorn.run(server)
```


to configure/run a real application, one would typically chain/apply a pile of middlewares and a handler:

```python

middleware_pile = apply_middleware(
    wrap_content_type(),
    wrap_static("/static/data"),
    wrap_routes(routes),
    wrap_parameters(),
    wrap_cookies,
    wrap_json,
)

server = build_server(middleware_pile(standard_not_found))
```
## Features

Nothing is enabled by default. Every functionality has its own middleware.  

### Routing
To include `shallot`s builtin routing functionality, use the routing-middleware: `wrap_routes`.

routing is one essential and by far, the most opinionated part of any webframeworks-api. `shallot` is no exception there. Routing is defined completely via a data-structure:

```python
async def hello_world(request):
    return text("hi user!")

# is attached to a "dynamic"-route with one parseable url-part
async def handle_index(request, idx):
    return text(f"hi user number: {idx}")


routes = [
    ("/", ["GET"], hello_world),
    ("/hello", ["GET"], hello_world),
    ("/hello/{index}", ["GET"], handle_index),
    ("/echo", ["GET", "PUT", "POST"], post_echo),
    ("/json", ["GET", "PUT"], show_and_accept_json),
]

```
as shown above, `routes` is a list of tuples with:
    
    1. the (potentially dynamic) route
    2. the allowed methods
    3. the handler

Routes with an `{tag}` in it, are considered dynamic-routes. The router will parse the value from the url and transfered it (as string) to the handler-function. Therfore the handler function must accept the `request` and as many arguments as there are `{tag}`s.

### JSON
to easily work with json-data, use the json-middleware `wrap_json`:

every request, that contains a content-type `application/json` will be parsed and the result will be attached to the request under the key `json`. 
When data body is not parseable as json, the middleware will respond with `{"status": 400, "body": "Malformed JSON"}`.

when you want to return json-data as your response, use the `shallot.response` - function `json`:

```python
from shallot.response import json

async def json_handler(request):
    client_json_data = request.get("json")
    assert isinstance(client_json_data, dict)

    return json({"hello": "world"})
```

### Static-Files

`shallot` is not optimized to work as static-file-server. Although it goes to great lengths, to provide a solid experience for serving static content.

To work with static-files use the `wrap_static` - middleware.

This middleware depends on `aiofiles`.

```python
import os
here = os.path.dirname(__file__)
wrap_static("/static/data", root_path=here)  # will always assume the folder is located : <this_file>.py/static/data
```
Browser-caches will be honored. For that, `last-modified` and `etag` - headers will be sent accordingly. 
Requests with a path containing "../" will be automatically responded with `404-Not Found`.

### Websockets

In shallot, websockets are modeled as async-generators. Except that, websockets-handlers are more or less equal to http-handlers.
They receive data, `str` or `bytes` from the generator (`receiver`) and a `dict` from the opening http-request (`request`). As a
result a websocket-handler yields back data (`dict`), in the example below, constructed via `ws_send`


```python
@websocket
async def echo_server(request, receiver):
    async for message in receiver:
        yield ws_send(f"@echo: {message}")

```



