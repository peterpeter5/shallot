# shallot - a plugable "webframework"

## What is a shallot?

It is a small onion. It has only small and few layers. When you use it (cut it for cocking), it does not make 
you cry (that much).

The above description of the vegetable, is a good misson-statement for what `shallot` (the [micro-] "webframework") tries to be. 

`shallot` is a small layer on top of an ASGI - compatible server, like: uvicorn, hypercorn, ... It is haveliy inspired 
by [ring](https://github.com/ring-clojure/ring). The main differnce to other webframeworks is, that `shallot` is easly pugable and extensible. Every component can be switched and new features can be added without touching `shallot`s source-code. That is accomplished by using middlewares for every functionality in `shallot`.

## Architecture

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

### handler

`shallot` gets a request (dict) and calls a user-provided handler. A `handler` is an async-function that takes a request and returns a response-dict. That's all.  

```python
async def handler(request):
    return {"status": 200}
```

### middleware

All of `shallot`s functionality is implemented via middlewares. That makes it possible to easily extend, configure or change `shallot`s behaviour. In fact: if you don't like the implementation of a certain middleware, just write your own and use it insetad (or better: enhance `shallot` via PR)!

The general functionality of a middleware, is that it wraps a handler-function-call. Middlewares are designed that way, that they can be composed / chained together. So for a middleware-chain with 3 different middlewares, a call chain might look like:

```
|-> middleware 1 (enter)
    |-> middleware 2 (enter)
        |-> middleware 3 (enter)
            |-> handler (execute)
        |<- middleware 3 (leave)
    |<- middleware 2 (leave)
|<- middleware 1 (leave)
```

#### middleware signature

in order to make middlewares composeable / work together, thy must implement the following signature:

```python
def wrap_print_logging(next_middleware):
    async def _log_request_response(handler, request):
        print(f"Request to the handler: {request}")
        
        response = await next_middleware(handler, request)
        
        print(f"Response from the handler: {response}")
        return response
    return _log_request_response
```

The above example shows middleware that would simply printout the request and the reponse from the handler. Every middleware will run for EVERY request that comes to your application!


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

### static-files

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
By defalult `symlinks` are forbidden. You can override this via parameter in `wrap_static`-function. 

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

    1. *string*: the value will be sent *as-is* without further checking, whether it complies to a date-format.
    2. *int*|*float*: the value will be interpreted as a timestamp and will be converted to a date-string

#### Deleting Cookies

To delete a cookie you will need to set the cookie-value to None:

```python
{"cookie-name": None}
```
Then a cookie will be send, with an `expires`-value in the past.





