# Cookies

Cookies are handled as dict's. To use cookie-handling one must include `wrap_cookies` in the middleware-chain.

```python
build_server(apply_middleware(wrap_cookies())(handler))
```
## Examples

### Receive Cookies

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

### Set Cookies

Cookies are send to the client, when the response contains a `cookies`-key. The `cookies`- value is a dict, with the minimal structure:
```python
{"cookie-name": {"value": 0}}
```

This will result in a *session-cookie* : `{"cookie-name": 0}`, which will be sent with the next request. Further data can be attached to the cookie. The supported keys are, all names that are supported by [python-std-lib:morsel](https://docs.python.org/3/library/http.cookies.html#http.cookies.Morsel):

    - expires
    - path
    - comment
    - domain
    - max-age
    - secure
    - version
    - httponly

The `expires` value can be set in two different fashions: 

1. `string`: the value will be sent *as-is* without further checking, whether it complies to a date-format.
2. `int`|`float`: the value will be interpreted as a timestamp and will be converted to a date-string

### Deleting Cookies

To delete a cookie you will need to set the cookie-value to None:

```python
{"cookie-name": None}
```
Then a cookie will be sent, with an `expires`-value in the past.
