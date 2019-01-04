# Parameters
parameters are url-encoded query-strings or bodies. To automatically parse this data use the `wrap_parameters` - middleware
```python

from shallot.middlewars import wrap_parameters
build_server(apply_middleware(
    wrap_parameters(keep_blank_values=False, strict_parsing=False, encoding='utf-8')
) (handler))
```
Parameters (url-query or form-body-data) is parsed to a `dict`. The value(s) are added to a list. The middleware is mostly a wrapper to the python-builtin [urllib.parse.parse_qs](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.parse_qs). All parameters to `wrap_parameters` are passed to `parse_qs`. 

This middleware will add 3 keys to the request. URL-query-strings  will be parsed and added to `query_params`. If the body is sent with the content-type `application/x-www-form-urlencoded`, the body will parsed and added to `form_params`. The result of merging `query_params` and `form_params` will be added to the `params`-key.

## Examples

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
## Discussion

The values of the parameter-dict's are treated as list on purpose. Because every key can be sent multiple-times, every application has to handle the possibility of getting parameters as lists.

There are three possibilities how to deal with this situation: 

1. When parameter-key is sent only once return a string, otherwise return a list.

2. Return a special-`dict` or `class` that supports special-access-semantic for parameters

3. Always return lists and let the application deal with it.


The first solution is very convenient for simple use-cases. As long as your clients are sending every key only a once, you can access the value without further hassle simply as a `string`. The downside for this solution is that, you might forget to handle the `list`-case.  

The second solution can be nice. Other webframework's like `sanic` use this. But it is against the philosophy of `shallot`. `shallot` tries very hard to model every thing, as simple as possible. Therefore it tries to use only "standard"-data-structures and functions. 

The third solution is the one chosen by `shallot`. It is less convenient on simple use cases, but it provides one type and no special-cases to deal with. 
 