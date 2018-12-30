import json
from shallot.response import respond400


def wrap_json(next_middleware):
    async def json_result(handler, request):
        content_type = request.get("headers", {}).get("content-type", "")
        if "application/json" in content_type:
            try:
                body = request["body"].decode()
                data = json.loads(body)
                request["json"] = data
            except json.JSONDecodeError:
                return respond400("Malformed JSON")
        else:
            request["json"] = None
        return await next_middleware(handler, request)

    return json_result
