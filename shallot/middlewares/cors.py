def wrap_cors(allow_origin="*"):
    def wrap_cors_handler(next_middleware):
        async def cors_result(handler, request):
            result = await next_middleware(handler, request)
            new_headers = {
                **result.get("headers", {}),
                "Access-Control-Allow-Origin": allow_origin,
            }
            result["headers"] = new_headers
            return result

        return cors_result

    return wrap_cors_handler
