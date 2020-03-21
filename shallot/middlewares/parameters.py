from urllib.parse import parse_qs


def wrap_parameters(keep_blank_values=False, strict_parsing=False, encoding="utf-8"):
    def middleware(next_middleware):
        async def _wrap_params(handler, request):
            qs = request.get("query_string")
            if qs:
                qs = qs.decode(encoding) if isinstance(qs, bytes) else qs
                query_params = parse_qs(
                    qs, keep_blank_values=keep_blank_values, strict_parsing=strict_parsing, encoding=encoding,
                )
            else:
                query_params = {}

            request_content_types = request.get("headers", {}).get("content-type", "")
            if "application/x-www-form-urlencoded" in request_content_types:
                form_params = parse_qs(
                    request["body"].decode(encoding),
                    keep_blank_values=keep_blank_values,
                    strict_parsing=strict_parsing,
                    encoding=encoding,
                )
            else:
                form_params = {}

            params = {**query_params, **form_params}

            request["params"] = params
            request["query_params"] = query_params
            request["form_params"] = form_params

            return await next_middleware(handler, request)

        return _wrap_params

    return middleware
