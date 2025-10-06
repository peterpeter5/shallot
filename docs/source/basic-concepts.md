# The basic concepts 


## Overview

`shallot` models a http-request-response-cycle as single function call. It treats `request` and `response` as `dict`s. The request get passed to a `handler`-function (which itself can be "middleware-decorated") and the `handler` produces a response.
Basically `shallot` works like this:
1. take the ASGI [connection-scope](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope) (`dict`)
2. read the body of the request and attach the body (`bytes`) to scope-dict 
3. pass the request-`dict` (scope + attached body) to a user-defined function (called `handler`)
4. the result (`response`) of a handler has to be a `dict`. The response must at least provide a `status`-key with an integer. If provided a `body`-key for the response is provided, than the value must be of type `bytes` and to will be transferred to the client. 

## data-flow

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

## request

The `request` is always the first argument that gets passed to your `handler`-function. It is of type `dict`. It has basically the same content than the [ASGI-connection-scope](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope). 

A request will at least have the following structure:

- `type`: http [string]
- `http_version`: one of `1.0`, `1.1` or `2` [`string`]
- `method`: the http-verb in uppercase (for example: "GET", "PUT", "POST", ...) [`string`]
- `scheme` [optional, but not empty]: the url-scheme (for example: "http", "https") [`string`]
- `query_string`: Byte-string with the url-query-path content (everything after the first `?`) [`bytes`]
- `root_path`: mounting-point of your application [`string`]
- `client`: A two-item iterable of `[host, port]`, where host is a unicode string of the remote host’s IPv4 or IPv6 address, and port is the remote port as an integer. Optional, defaults to None. [`list`|`tuple`]
- `server`: A two-item iterable of `[host, port]`, where host is the listening address for this server as a unicode string, and port is the integer listening port. Optional, defaults to None. [`list`|`tuple`]
- `headers`: a `dict` with all header-names as `keys` and the corresponding-values as `values` of the dict. Duplicated `headers` will be joined "comma-separated". All header-names are lower-cased. [`dict`]
- `headers_list`: the original `headers`-data-structure form the ASGI-connection-scope. This is a `list` containing `tuples` in the form: `[(header-name1, header-value1), ...]`. The header-names can be duplicated. [This is the basis for `headers`]
- `body`: The body of the http-request as `bytes`. `shallot` always read the entire body and then calls the `handler`-function. [`bytes`] 

## response

The `response` is the result of the function-call to the handler (with the `request` as first argument). The `response` has to be a `dict`. The response must have the following structure:

- `status`: the http-return-code [`int`]
- `body` [optional]: the body of the http-response [`bytes`]
- `headers` [optional]: the http-response-headers to be used. The value is a `dict` (for example: `{"header1-name": "header1-value", ...}`)
- `stream` [optional]: this must be an `async-iterable` yielding `bytes`. When the `response` contains a key named `stream`, than `shallot` will consume the `iterable` and will stream the provided data to the client. This is specially useful for large response-bodies.

## handler

`shallot` assembles a request-dict and calls a user-provided handler. A `handler` is an async-function that takes a request and returns a response (`dict`).  

```python
async def handler(request):
    return {"status": 200}
```

## middleware

Most of `shallot`s  functionality is implemented via middlewares. That makes it possible to easily extend, configure or change `shallot`s behavior. In fact: if you don't like the implementation of a certain middleware, just write your own and use it instead (or better: enhance `shallot` via PR)!

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

### middleware signature

in order to make middlewares composeable / work together, thy must implement the following signature:

```python
def wrap_print_logging(next_middleware):
    async def _log_request_response(handler, request):
        print(f"Request to the handler: {request}")
        
        response = await next_middleware(handler, request)  # IMPORTANT: here we call the middlewares and wait for them to run
        
        print(f"Response from the handler: {response}")
        return response
    return _log_request_response
```

The above example shows a middleware that would simply printout the request and the response from the handler. Every middleware will run for EVERY request that comes to your application!

### composing middlewares together

`middlewares` are great because they can be composed/chained together. In that way every `middleware` can enhance the `request` / `response` or choose a different `handler` to add functionality. Chaining middlewares is done via the `apply_middleware` - function provided by shallot:

```python
from shallot.middlewares import chain_middleware
middlewares = chain_middleware(middleware1, middleware2, middleware3)

enhanced_handler = middlewares(default_handler)
```

The result of `chain_middleware` is a middleware-chain. A middleware-chain is a function that accepts another function, the `default_handler`. This is the handler-function that gets called after the request is passed through all middlewares. After instantiating the middleware-chain with a handler, the result is another-function. The function behaves just like a normal `handler`-function and can be used with `build_server`

### differences to ring-middleware (discussion)
While the function-signature of a `shallot`-handler is the same as with [ring](https://github.com/ring-clojure/ring), the middleware-signature is different and slightly more complex. This is, to support "request-routing" as a middleware. This way, the router can be just another middleware choosing a new handler, instead of enhancing the request. This way, other middlewares (possible type-annotation-aware middlewares) can be chained after the router and have access to the handler-function. 

## run an application with an ASGI-server

the minimal deployable thing one can build is this:

```python
from shallot import build_server

async def minimal(request):
    """
    answer EVERY request with 200 and NO body 
    """
    return {"status": 200}

server = build_server(minimal)

if __name__ == "__main__":
    import uvicorn  # shallot is not tied to uvicorn, its just fast
    uvicorn.run(server, "127.0.0.1", 5000, log_level="info", debug=True)
```

to configure/run a real application, one would typically chain/apply a pile of middlewares and a handler:

```python

async def handle_404(request):
    return {"status": 404}

middleware_pile = apply_middleware(
    wrap_cors(),
    wrap_content_type(),
    wrap_static("/static/data"),
    wrap_routes(routes),
    wrap_cookies(),
    wrap_json(),
)

server = build_server(middlewre_pile(handle_404))
```
