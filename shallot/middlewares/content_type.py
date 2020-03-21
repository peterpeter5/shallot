from mimetypes import guess_type, add_type


def wrap_content_type(
    additional_content_types=None, default_content_type="application/octet-stream", strict=False,
):

    additional_content_types = {} if additional_content_types is None else additional_content_types
    for cont_type, extensions in additional_content_types.items():
        for ext in extensions:
            ext = "." + ext.lstrip(".")
            add_type(cont_type, ext, strict)

    def wrap_handler(next_middleware):
        async def add_content_type(handler, request):
            response = await next_middleware(handler, request)
            response_headers = response.get("headers", {})
            if not response_headers or not response_headers.get("content-type"):
                guessed_type, guessed_encoding = guess_type(request["path"], strict=strict)
                if guessed_type:
                    response_headers["content-type"] = guessed_type
                else:
                    response_headers["content-type"] = default_content_type

                response["headers"] = response_headers
            return response

        return add_content_type

    return wrap_handler
