# Static-Files

`shallot` is not optimized to work as static-file-server. Although it goes to great length, to provide a solid experience for serving static content.

to work with static-files use the `wrap_static` - middleware:
```python
rel_path_to_folder_to_serve_from = "/static/data"
build_server(apply_middleware(wrap_static(rel_path_to_folder_to_serve_from))(handler))
```

## Examples

This middleware depends on `aiofiles`. It will try to match the path of a request, to files in the folder used when "instantiating" the middleware (in the example above: `/static/data`) relative to your current $PWD / %CWD%. To provide a `cwd` independent path, call `wrap_static` with a root-path:

```python
import os
here = os.path.dirname(__file__)
wrap_static("/static/data", root_path=here)  # will always assume the folder is located : <this_file>.py/static/data
```

Browser-caches will be honored. For that, `last-modified` and `etag` - headers will be sent accordingly. When the browser requests a already-cached resource (`if-none-match` or/and `if-modified-since` in request headers), this middleware will reply with a `304-Not Modified`.
For further information about browser-file-caches: [MDN:Cache validation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching#validation)

``` note:: Requests with a path containing "../" will be automatically responded with *404-Not Found*.
```
