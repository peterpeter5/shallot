# JSON
to easily work with json-data, use the json-middleware:
```python
from shallot import build_server
from shallot.middlewares import wrap_json

server = build_server(apply_middleware(wrap_json())(handler))

```
every request, that contains a content-type `application/json` will be parsed and the result will be attached to the request under the key `json`. 
When data body is not parse-able as json, the middleware will respond with `{"status": 400, "body": "Malformed JSON"}`.

When the client does not send a body, the default mode is to set the 'json'-key to None `request["json"] == None`. You can change this behavior with `wrap_json(fail_on_missing_body=True)`. Then `{"status": 400, "body": "Malformed JSON"}` is returned.


## Examples

When you want to return json-data as your response, use the `shallot.response` - function `json`:

```python
from shallot.response import json

async def json_handler(request):
    return json({"hello": "world"})
```
