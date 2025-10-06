import json
from shallot.response import respond400


def wrap_json(fail_on_missing_body=False):
    def _wrap_json(next_middleware):
        async def json_result(handler, request):
            content_type = request.get("headers", {}).get("content-type", "")
            is_right_content_type = "application/json" in content_type
            has_body = bool(request.get("body"))

            if is_right_content_type and has_body:
                try:
                    body = request["body"].decode()
                    data = json.loads(body)
                    request["json"] = data
                except json.JSONDecodeError:
                    return respond400("Malformed JSON")
            elif is_right_content_type and not has_body and fail_on_missing_body:
                return respond400("Malformed JSON")
            else:
                request["json"] = None
            return await next_middleware(handler, request)

        return json_result

    return _wrap_json
