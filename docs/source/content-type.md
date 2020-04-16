# Content-Types

For static-files it can be convenient to use the content-type-middleware: `wrap_content_type`
So when a resource is requested, for example: "/static/index.html", then this middleware will set the `content-type`-header to `text/html`

```python

server = build_server(apply_middleware(
    wrap_content_type())(handler)
)
```
By default, it will guess the content-type based on the python-builtin `mimetypes` with non-strict evaluation. To change this behavior one can provide a `strict=True` flag to `wrap_content`.


When the content-type can not be guessed, "application/octet-stream" is used. This can be overridden via `wrap_content_type`.

This middleware will only add a `content-type`-header when none is provided in the response.  

Additional type->extension-mappings can be provided to `wrap_content_type` via dict:

```python
add_mapping = {"application/fruit": [".apple", "orange"]}
apply_middleware(wrap_content_type(additional_content_types=add_mapping))
```

the key is the content-type to map to, and the value is a list of extensions (with or without leading-dot)
