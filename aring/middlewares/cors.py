def wrap_cors(allow_origin="*"):
    def wrap_cors_handler(handler):
        async def cors_result(request):
            result = await handler(request)
            new_headers = {**result.get("headers", {}), "Access-Control-Allow-Origin": allow_origin}
            result["headers"] = new_headers
            return result
        return cors_result
    return wrap_cors_handler