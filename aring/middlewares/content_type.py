import re
from mimetypes import guess_type, add_type

def wrap_content_type(additional_content_types=None):
    """
    :param additional_content_types: 
    """
    additional_content_types = {} if additional_content_types is None else additional_content_types
    def wrap_handler(handler):
        async def add_content_type(request):
            response = await handler(request)
            response_headers = response.get("headers", {})
            if not response_headers or not response_headers.get("content-type"):
                guessed_type, guessed_encoding = guess_type(request["path"], strict=False)
                if guessed_type:
                    response_headers["content-type"] = guessed_type
                elif response.get("stream", None) is None:
                    response_headers["content-type"] = "text/plain"
                else:
                    response_headers["content-type"] = "application/octet-stream"
                
                response["headers"] = response_headers
            return response

        return add_content_type
    return wrap_handler