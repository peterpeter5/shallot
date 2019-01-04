# Routing
To include `shallot` builtin routing use the routing-middleware: `wrap_routes`:
```python
build_server(apply_middleware(wrap_routes(routes))(default_handler))
```
The routing-middleware is somewhat special, to other middlewares. It does not enhance the request/response, but chooses a new handler for the specific request. If the router can't find a matching handler for the route, then the `default_handler` will be passed into the next middleware(s).

## Examples

Routing is completely defined via a data-structure:

```python
async def hello_world(request):
    return text("hi user!")

# handle_index is attached to a "dynamic"-route with one parseable url-part -> thus it needs to accept request and one additional parameter
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

routes with an `{tag}` in it, are considered dynamic-routes. The router will parse the value from the url and passed it (as string) to the handler-function as parameter. Therefor the handler function must accept the `request` and as many arguments as there are `{tag}`s.

## Discussion

maybe one controversial one upfront: trailing slashes are ignored. In the defined routes and in the matching of requests too.


routing is one essential and by far, the most opinionated part of any webframeworks-api. `shallot` is there no exception. 


