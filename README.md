# shallot - a plugable "webframework"

## What is a shallot?

It is a small onion. It has only small and few layers. When you use it (cut it for cooking), it does not make 
you cry (that much).

The above description of the vegetable, is a good misson-statement for what `shallot` (the [micro-] "webframework") tries to be. 

`shallot` is a small layer on top of an ASGI - compatible server, like: uvicorn, hypercorn, ... It is haveliy inspired 
by [ring](https://github.com/ring-clojure/ring). The main differnce to other webframeworks is, that `shallot` is easly pugable and extensible. Every component can be switched and new features can be added without touching `shallot`s source-code. That is accomplished by using middlewares for nearly every functionality in `shallot`.

## Architecture

`shallot` is an [ASGI](https://asgi.readthedocs.io/en/latest/index.html) - compatible webframework. 

### Basic-Concepts

`shallot` models a http-request-response-cycle as single function call. It treats `request` and `response` as `dict`s. The request get passed to a `handler` (which itself can be "middleware-decorated") and the `handler` produces a response.
Basically `shallot` works like this:
1. take the ASGI [connection-scope](https://asgi.readthedocs.io/en/latest/specs/www.html#connection-scope) (`dict`)
2. read the body of the request and attach the body (`bytes`) to scope-dict 
3. pass the request-`dict` (scope + attached body) to a user-defined function (called `handler`)
4. the result (`response`) of a handler has to be a `dict`. The response must at least provide a `status`-key with an integer. If provided a `body`-key for the response is provided, than the value must be of type `bytes` and to will be transfered to the client. 

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

### response

The `response` is the result of the function-call to the handler (with the `request` as first argument). The `response` has to be a `dict`. The reponse must have the following structure:

- `status`: the http-return-code [`int`]
- `body` [optional]: the body of the http-response [`bytes`]
- `headers` [optional]: the http-response-headers to be used. The value is a `dict` (for example: `{"header1-name": "header1-value", ...}`)
- `stream` [optional]: this must be an `async-iterable` yielding `bytes`. When the `response` contains a key named `stream`, than `shallot` will consume the `iterable` and will stream the provided data to the client. This is specially usefull for large response-bodies.

### handler

`shallot` assembles a request-dict and calls a user-provided handler. A `handler` is an async-function that takes a request and returns a response (`dict`).  

```python
async def handler(request):
    return {"status": 200}
```

### middleware

Most of `shallot`s  functionality is implemented via middlewares. That makes it possible to easily extend, configure or change `shallot`s behaviour. In fact: if you don't like the implementation of a certain middleware, just write your own and use it insetad (or better: enhance `shallot` via PR)!

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

#### middleware signature

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

The above example shows a middleware that would simply printout the request and the reponse from the handler. Every middleware will run for EVERY request that comes to your application!

#### composing middlewares together

`middlewares` are great because they can be composed/chained together. In that way every `middleware` can enhance the `request` / `response` or choose a different `handler` to add functionality. Chaining middlewares is done via the `apply_middleware` - function provided by shallot:

```python
from shallot.middlewares import chain_middleware
middlewares = chain_middleware(middleware1, middleware2, middleware3)

enhanced_handler = middlewares(default_handler)
```

The result of `chain_middleware` is a middleware-chain. A middleware-chain is a function that accepts another function, the `default_handler`. This is the handler-function that gets called after the request is passed through all middlewares. After instantiating the middleware-chain with a handler, the result is another-function. The function behaves just like a normal `handler`-function and can be used with `build_server`

#### differences to ring-middleware
While the function-signature of a `shallot`-handler is the same as with [ring](https://github.com/ring-clojure/ring), the middleware-signature is different and slitely more complex. This is, to support "request-routing" as a middleware. This way, the router can be just another middleware choosing a new handler, instead of enhancing the request. This way, other middlewares (possible type-annotation-aware middlewares) can be chained after the router and have access to the handler-function. 

### run an application

the minimal deployable thing one can build is this:

```python
async def minimal(request):
    """
    answer EVERY request with 200 and NO body 
    """
    return {"status": 200}

server = build_server(minimal)

if __name__ == "__main__":
    import uvicorn  # shallot is not tied to uvicorn, its just fast
    uvicorn.run("127.0.0.1", 5000, log_level="info", debug=True)
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
    wrap_cookies,
    wrap_json,
)

server = build_server(middlewre_pile(handle_404))
```

## Features

Nothing is enabled by default. Every functionality has its own middleware.  

### Routing
To include `shallot` builtin routing use the routing-middleware: `wrap_routes`:
```python
build_server(apply_middleware(wrap_routes(routes))(default_handler))
```
The routing-middleware is somewhat special, to other middlewares. It does not enhance the request/response, but chooses a new handler for the specific request. If the router can't find a matching handler for the route, then the `default_handler` will be transfered into the next middleware(s).

routing is one essential and by far, the most opinonated part of any webframeworks-api. `shallot` is there no exception. Routing is defined completely via a data-structure:

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

routes with an `{tag}` in it, are considered dynamic-routes. The router will parse the value from the url and transfered it (as string) to the handler-function. Therfore the handler function must accept the `request` and as many arguments as there are `{tag}`s.

maybe one controversial one upfront: trailing slashes are ignored. In the defined routes and in the matching of requests too.



### JSON
to easily work with json-data, use the json-middleware:
```python
build_server(apply_middleware(wrap_json)(handler))
```
every request, that contains a content-type `application/json` will be parsed and the result will be attached to the request under the key `json`. 
When data body is not parseable as json, the middleware will respond with `{"status": 400, "body": "Malformed JSON"}`.

when you want to return json-data as your response, use the `shallot.response` - function `json`:

```python
from shallot.response import json

async def json_handler(request):
    return json({"hello": "world"})
```

### Parameters
parameters are url-encoded query-strings or bodies. To automatically parse this data use the `wrap_parameters` - middleware
```python

from shallot.middlewars import wrap_parameters
build_server(apply_middleware(
    wrap_parameters(keep_blank_values=False, strict_parsing=False, encoding='utf-8')
) (handler))
```
Parameters (url-query or form-body-data) is parsed to a `dict`. The value(s) are added to a list. The middleware is mostly a wrapper to the python-builtin [urllib.parse.parse_qs](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.parse_qs). All parameters to `wrap_parameters` are passed to `parse_qs`. 

This middleware will add 3 keys to the request. URL-query-strings  will be parsed and added to `query_params`. If the body is sent with the content-type `application/x-www-form-urlencoded`, the body will parsed and added to `form_params`. The result of merging `query_params` and `form_params` will be added to the `params`-key.

```python
async def return_request(request):
    return request


handle_request = apply_middleware(wrap_parameters())(return_request)

url_request = {"query_string": b"key1=0&p2=val&p2=9"}
print(handle_request(url_request))
>> {
    "query_string": b"p2=9&key1=0&p2=val",
    "query_params": {
        "key1": ["0"],
        "p2": ["9", "val"]
    },
    "form_params": {},
    "params": {
        "key1": ["0"],
        "p2": ["9", "val"]
    },
}

form_request = {
    "headers": {"content-type": "application/x-www-form-urlencoded"},
    "body": b"p2=9&key1=0&p2=val" 
}

print(handle_request(form_request))
>> {
    "body": b"p2=9&key1=0&p2=val",
    "query_params": {},
    "form_params": {
        "key1": ["0"],
        "p2": ["9", "val"]
    },
    "params": {
        "key1": ["0"],
        "p2": ["9", "val"]
    },
}


mixed_request = {
    "query_string": b"u1=0&u8=3",
    "headers": {"content-type": "application/x-www-form-urlencoded"},
    "body": b"p2=9&key1=0&p2=val",
} 
print(handle_request(mixed_request))
>> {
    "body": b"p2=9&key1=0&p2=val",
    "query_string": b"u1=0&u8=3",

    "query_params": {
        "u1": ["0"],
        "u8": ["val"],
    },
    "form_params": {
        "key1": ["0"],
        "p2": ["9", "val"]
    },
    "params": {
        "key1": ["0"],
        "p2": ["9", "val"],
        "u1": ["0"],
        "u8": ["val"],
    },
}
```

*The values are treated as list on purpose. Because every key can be sent multiple-times, it is better to consequently deal with lists. Otherwise an application would have to handle 2 different types (which both support iterating/indexing), rather than with different-length lists.*


### Static-Files

`shallot` is not optimized to work as static-file-server. Altough it goes to great length, to provide a solid experience for serving static content.

to work with static-files use the `wrap_static` - middleware:
```python
rel_path_to_folder_to_serve_from = "/static/data"
build_server(apply_middleware(wrap_static(rel_path_to_folder_to_serve_from))(handler))
```

This middleware depends on `aiofiles`. It will try to match the path of an request, to files in the folder `/static/data` relative to your current $PWD / %CWD%. To provide a `cwd` indepented path, call `wrap_static` with a root-path:

```python
import os
here = os.path.dirname(__file__)
wrap_static("/static/data", root_path=here)  # will always assume the folder is located : <this_file>.py/static/data
```

Browser-caches will be honored. For that, `last-modified` and `etag` - headers will be send accordingly. When the browser requests a already-cached resource (`if-none-match` or/and `if-modified-since`), this middleware will reply with a `304-Not Modified`.
For further information about browser-file-caches: [MDN:Cache validation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching#Cache_validation)

Requests with a path containing "../" will be automatically responded with `404-Not Found`.

### Content-Types

for static-files it can be convenient to use the content-type-middleware: `wrap_content_type`
So when a resource is requested, for example: "/static/index.html", then this middleware will set the `content-type`-header to `text/html`

```python

server = build_server(apply_middleware(
    wrap_content_type())(handler)
)
```
By defalut it will guess the content-type based on the python-builtin `mimetypes`. The default is to use `mimetypes` with non-strict evaluation. To change this behaviour one can provide a `strict=True` falg to `wrap_content`.

When the content-type can not be guessed, "application/octet-stream" is used. This can be overriden via `wrap_content_type`.

This middleware will only add a `content-type`-header when none is provided in the response.  

Additional type->extension-mappings can be provided to `wrap_content_type` via dict:

```python
add_mapping = {"application/fruit": [".apple", "orange"]}
apply_middleware(wrap_content_type(additional_content_types=add_mapping))
```

the key is the content-type to map to, and the value is a list of extensions (with or without leading-dot)


### Cookies

Cookies are handled as dicts. To use cookie-handling one must include `wrap_cookies` in the middleware-chain.

```python
build_server(apply_middleware(wrap_cookies)(handler))
```

#### Receive Cookies

Cookies send with the request, are parsed and attached to the request-object with the key `cookies`. For further information about cookies and how to use them: [MDN:cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)

```python
async def handler(request):
    print(request["cookies"])  # prints {a-cookie-name: value, b-cookie-name: value}

    return {
        "status": 200, 
        "cookies": {
            "first": {
                "value": 3.4,
                "expires": 1545335438.5059335,
                "path": "/some/path",
                "comment": "usefull comment",
                "domain": "my.domain.zz",
                "max-age" 3600,
                "secure": True,
                "version": 2,
                "httponly": True,
            },
            "second": {"value": "value-asdf", "expires": "Thu, 20 Dec 2018 19:50:38 GMT"},
            "minimal": {"value": 0}.
            "to-delete": None,
        },
    }
```

#### Set Cookies

Cookies are send to the client, when the response contains a `cookies`-key. The `cookies`- value is a dict, with the minimal structure:
```python
{"cookie-name": {"value": 0}}
```

This will result in a *session-cookie* : `{"cookie-name": 0}`, which will be sent with the next request. Further data can be attached to the cookie. The supported keys are, all names that are supported by [python-std-lib:morsel]("https://docs.python.org/3/library/http.cookies.html#http.cookies.Morsel"):

    - expires
    - path
    - comment
    - domain
    - max-age
    - secure
    - version
    - httponly

The `expires` value can be set in two diffrent fashions: 

    1. string: the value will be sent *as-is* without further checking, whether it complies to a date-format.
    2. int|float: the value will be interpreted as a timestamp and will be converted to a date-string

#### Deleting Cookies

To delete a cookie you will need to set the cookie-value to None:

```python
{"cookie-name": None}
```
Then a cookie will be send, with an `expires`-value in the past.





