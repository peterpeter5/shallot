Tutorial
========
.. note::
    This tutorial implies that you have read introduction-guide: :doc:`basic-concepts`.

.. note:: 
    This tutorial uses CPython36


Installation
+++++++++++++

You can install `shallot` via pip:

.. code-block:: bash

    pip install shallot

As `shallot` is just an application-framework it does not come with a builtin server. You can use any ASGI-compliant server, but for this tutorial we will use `uvicorn`:

.. code-block:: bash

    pip install uvicorn


Hello World
++++++++++++

Our first goal will be to start a server, with a simple `handler` that will greet us.

To do that we create file called `00-tutorial.py` and write our first handler:

.. code-block:: python

    from shallot import build_server
    

    async def greetings(request):
        return {"status": 200, "body": b"Hello you!"}  # NOTE: we return bytes as body!

    hello_world_app = build_server(greetings)

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(hello_world_app, "127.0.0.1", 5000, debug=True)

Run this python-file with:

.. code-block:: bash

    python 00-tutorial.py

Now a webserver should start and when you point your browser to the address: "http://127.0.0.1:5000/", than
you should see your greeting rendered.

Setting headers for the response
---------------------------------

Now enable the debug-tools of your browser
(for `firefox` and `chrome` press F12), navigate to the "network"-tab 
and reload the page. As you can see in the "/"-GET request, the response does
not contain a proper `content-type` - header. 

Browser are very good in guessing the `content-type` of your response, but we
want to make the browsers life a little easier 
and extend our response with a `content-type`-header:

.. code-block:: python

    async def greetings(request):
        return {
            "status": 200, 
            "body": b"Hello you!",
            "headers": {"content-type": "text/plain"}
        }  

Stop your server (CTRL-C) and restart it. Reload the page and inspect the "/" - GET response.
Now you should see a correct `content-type` - header. 

To further improve our response, we will set the `content-length` - header too.
Go back to your handler function and add the  `content-length` - header:


.. code-block:: python

    async def greetings(request):
        message = b"Hello you!"
        return {
            "status": 200, 
            "body": message,
            "headers": {
                "content-type": "text/plain",
                "content-length": str(len(message))
            }
        }  

Restart your app again, reload the page and inspect the response-headers. 
Now we are returning a proper http-request. 

Because it is tedious to always set these headers and and to encode your body to `bytes`,
`shallot` ships with some builtin-response-functions, to make your life easier.

One of these functions is the `text` function from the `response`-module. 
Refactor your code this:

.. code-block:: python

    from shallot import build_server
    from shallot.response import text


    async def greetings(request):
        return text("Special greetings to you, my dear reader")


    hello_world_app = build_server(greetings)

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(hello_world_app, "127.0.0.1", 5000, debug=True)

The `response.text` - function takes a `string` as input
and returns a `dict`-similar to one we have constructed manually before.


Using the request-headers
--------------------------

As the next step, we will improve our greeting by using
the `user-agent` - header of the request. Now change your
`handler` - function in the following way:

.. code-block:: python

    async def greetings(request):
        user_agent = request["headers"].get("user-agent")
        return text(f"Special greetings to you: {user_agent}")

The `request` contains a key called `headers`. These are 
the request-headers. Normally your browser will set the `user-agent`
with each request. But other clients might not even send `headers` at all.
Then the `headers`-dict would be empty.
Thus we access the header name with `get` - function (instead of a `KeyError`, the `get` - method will return `None`, 
when the key is not present).

Serving static files
+++++++++++++++++++++

As you might have seen, your browser makes two requests when 
you reload your page. One GET-request for the path "/" and 
one GET-request for the path: "favicon.ico". At the moment 
we simply return the same response for both. But the browser 
wants to receive an icon that it could display. Thus no icon 
is visualized in your tab. 

Our next task will be, to correctly handle the "favicon.ico" - request.

First we create a new file called `01-tutorial.py`. Than we create a folder called `static`.
Now search for a suitable icon on the web or simply use the one
that is in shallot/tutorial/static.

.. important::

    In your folder `static` must be a image-file with the name
    `favicon.ico`


Than insert the following code into `01-tutorial.py`

.. code-block:: python

    from shallot import build_server
    from shallot.response import text
    from shallot.middlewares import apply_middleware, wrap_static


    async def greetings(request):
        user_agent = request["headers"].get("user-agent")
        return text(f"Special greetings to you: {user_agent}")


    middlewares = apply_middleware(
        wrap_static("./static")
    )

    greet_and_static_handler = middlewares(greetings)

    hello_world_app = build_server(greet_and_static_handler)

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(hello_world_app, "127.0.0.1", 5000, debug=True)

As you can see, the source-code has changed a bit. Our `handler` stays the
same, the main-part too. But we have imported a `middleware` called
`wrap_static`. 

`middlewares` are functions that *wrap* a handler and run with 
each request. For a better understanding of shallots middleware-concept
refer to the chapter middleware of :doc:`basic-concepts`.
Most of `shallots` functionality is implemented
via middlewares. This makes `shallot` completely configurable and easy
to extend with new functionality. `middlewares` must always be chained (even when it's just one)
with `apply_middleware`. The result of `apply_middleware` is a function that
expects to be called with a `handler`-function. Then we have a "enhanced" - handler
with extra functionality, which then can be used as the `handler` before 
(for example: used with `build_server`). 

The `wrap_static` - middleware handles 
static-files for you. It will scan your static-folder for the requested
file and if present will transmit it to the client. Now run your new app with:

.. code-block:: bash

    python 01-tutorial.py

Next reload your browser and look at the browser-tab. If everything worked
fine, than you should see your icon there. In the dev-tools network-tab you should
see a `200` or `304` status-code for the `favicon.ico` - request. This depends
on how often you have reloaded your page. When `wrap_static` transfers your
image for the first time, it will sent the image and set the 
appropriate "caching"-headers. So the next time, your browser asks for 
this resource, `shallot` will only transfer the content again, if the browser-cache
is not up-to-date. Otherwise it will just respond with `304- Not Modified`. This
way we can utilize the browser-cache and save network-traffic. 

When we inspect the `favicon.ico` - response - headers, we can see that the 
content-length is set correctly (for both the served file and the cache-response), but that
the `content-type` is missing again. Luckily for us, there is a `middleware` that
can handle this for us: `wrap_content_type`:

.. code-block:: python

    from shallot.middlewares import wrap_content_type

    middlewares = apply_middleware(
        wrap_content_type(),
        wrap_static("./static"),
    )

.. important:: 
    The order in which you apply the middlewares matters! `wrap_static` will
    "short-circuit" the request-chain and not call any `middlewares` or `handlers` that are 
    applied later, when it can answer the request. Thus `wrap_content_type` will
    never get called, when its applied after `wrap_static`.

Inspect the `favicon.ico` - request - response again. You should see a `content-type` - header. 
The value of the `content-type` - header should be: `image/vnd.microsoft.icon`. 
The value is guessed via the python-builtin-function: `mimetypes.guess_type` and can be customized.
For more information on this: :doc:`content-type`. 

Now we have a web-application which can handle basic-http-requests for dynamic
and static content.

Routing and JSON
+++++++++++++++++++

Our next goal will be to build a simple JSON-REST-service. This service will be 
a fruit-management-system. 

Our users will be able which-fruits we have and to obtain a detailed description and quantity
for each fruit. Additionally the user will be able to set the quantity for each fruit individually.

First create a new file, called `02-tutorial.py` and insert this:

.. code-block:: python

    from shallot import build_server
    from shallot.response import text, json
    from shallot.middlewares import apply_middleware, wrap_json, wrap_routes


    async def not_found(request):
        return text("Not Found", 404)

    fruit_store = {"oranges": 0, "apples": 0}


    async def fruit_collection(request):
        return json({"fruits": list(fruit_store.keys())})


    routes = [("/fruits", ["GET"], fruit_collection)]


    middlewares = apply_middleware(
        wrap_json,
        wrap_routes(routes)
    )
    fruit_app = build_server(middlewares(not_found))

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(fruit_app, "127.0.0.1", 5000, debug=True)

For the sake of this tutorial our database will be modeled as `dict` called `fruit_store`.
To satisfy our customer will have to implemented some different routes. Therefore we
use `shallots` builtin routing-middleware `wrap_routes`. `wrap_routes` will try to match
the `requests` - path value to a provided route, otherwise it will call the handler-function (default-handler)
the middleware-chain was instantiated with. Our default-handler is `not_found` and it will always
return `404 - Not Found`. To handle different routes, we create a routing-table
called `routes`. This is a list, containing tuples with at least 3 items:

1. a `string` with the route to match
2. a `list` of http-verbs (all in uppercase) for the desired verbs to handle
3. a function to actually handle the request for the given `path` and `method`

In our example, a `GET` - request to the path `"/fruits"` will be handled by `fruit_collection`.

Now start your new app via: 

.. code-block:: bash

    python 02-tutorial.py

and point your browser to "http://127.0.0.1:5000/fruits". If your browser is new
enough, it should render it as JSON. 

.. note:: 
    From now on, you should use a proper tool to debug your rest-api. You can 
    use python with the excellent `requests-package <http://docs.python-requests.org/en/master/>`_ or any 
    graphical rest-client you like.

As the next step we implement our details-view: 

.. code-block:: python

    fruit_store = {
        "oranges": {"descr": "an orange ball", "qty": 0, "name": "orange"}, 
        "apples": {"descr": "an green or red ball", "qty": 0, "name": "apple"}
    }


    async def fruit_collection(request):
        return json({"fruits": list(fruit_store.keys())})


    async def fruit_details(request, fruit_name):
        return json(fruit_store[fruit_name])

    routes = [
        ("/fruits", ["GET"], fruit_collection),
        ("/fruits/{name}", ["GET"], fruit_details)
    ]

We have updated our "database" `fruit_store` with additional information, 
and added a route for our detail-view. Now restart your app and make a get-request
to: "http://127.0.0.1:5000/fruits" the result should be unchanged to before: 

.. code-block:: python

    {
        "fruits": [
            "oranges",
            "apples"
        ]
    }

Next make a get-request to: "http://127.0.0.1:5000/fruits/oranges". Now you should
see:

.. code-block:: python
 
    {
        "descr": "an orange ball",
        "qty": 0,
        "name": "orange"
    }

as the response. What did we do to make this happen:

1. we created an additional route "/fruits/{name}". This route contains a "wildcard". This is signaled via `{anything-in-between}`. When a request is made to this route, than everything after "/fruits/" will be parsed as string and passed to the handler as arguments. 
2. we added a new handler `fruit_details` with 2 parameters (`request` and `fruit_name`)

So when we make a get-request "/fruits/apples", `apples` get parsed from the
`path` of the `request` and the `fruit_details` - function will be called with
the `request`-dict and `apples`. 

Lastly we'll have to implement the "change-quantity" - functionality. Therefore
we add a new route and handler-function:

.. code-block:: python

    from shallot import build_server
    from shallot.response import text, json
    from shallot.middlewares import apply_middleware, wrap_json, wrap_routes


    async def not_found(request):
        return text("Not Found", 404)

    fruit_store = {
        "oranges": {"descr": "an orange ball", "qty": 0, "name": "orange"}, 
        "apples": {"descr": "an green or red ball", "qty": 0, "name": "apple"}
    }


    async def fruit_collection(request):
        return json({"fruits": list(fruit_store.keys())})


    async def fruit_details(request, fruit_name):
        return json(fruit_store[fruit_name])

    async def change_quantity(request):
        data = request["json"]
        for fruit_name, new_qt in data.items():
            fruit_store[fruit_name]["qty"] = new_qt
        return  json({"updated": list(data.keys())})

    routes = [
        ("/fruits", ["GET"], fruit_collection),
        ("/fruits/{name}", ["GET"], fruit_details),
        ("/fruits", ["POST"], change_quantity)
    ]


    middlewares = apply_middleware(
        wrap_json,
        wrap_routes(routes)
    )
    fruit_app = build_server(middlewares(not_found))

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(fruit_app, "127.0.0.1", 5000, debug=True)


There are 2 things to note here. First we added a new routing-table entry, the third one, with
the same path as the first. This is OK, because the http-methods are different.
Second in the `change_quantity` - function we access the `json`-key from the `request-dict`.
This is possible, because we used the `wrap_json` - middleware. This middleware
parses JSON-requests for you and attaches the result to the `"json"` key of 
the `request-dict`. 

Next we make a post-request to "http://127.0.0.1:5000/fruits" with:

.. code-block:: python

    { "oranges": 3, "apples": 900}

and we should see:

.. code-block:: python 

    { "updated": ["oranges", "apples"]}

as the response. When revisiting the details-view of apples, we should see
the changed `quantity` too.

For more information about routing and JSON refer to the documentation:

- :doc:`json`
- :doc:`routing`
