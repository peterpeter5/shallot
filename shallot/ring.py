from collections import defaultdict
from asyncio import wait_for, Event
import sys
from itertools import chain
import logging
from functools import partial

__pytest__ = hasattr(sys, "_pytest_shallot_")

_ring_state = {}


def _reset_ring_state():
    global _ring_state
    _ring_state = {
        "lifetime": "No lifecyclemanagement provided from server.",
        "startup_event": None,
        "user_config": {},
    }


def _is_startup_completed():
    startup = _ring_state["startup_event"]
    return startup is None or startup.is_set()


def _init_startup():
    event = Event()
    event.clear()
    _ring_state["startup_event"] = event
    _ring_state["lifetime"] = "initialized"


def _mark_startup_completed(user_config):
    _ring_state["startup_event"].set()
    _ring_state["lifetime"] = "startup-completed"
    _ring_state["user_config"] = user_config


async def _wait_on_completed_startup():
    await _ring_state["startup_event"].wait()


def unicode2(xys, encoding="utf-8"):
    x, y = xys
    return (x.decode(encoding), y.decode(encoding))


def lowercase_key(xys):
    x, y = xys
    return (x.lower(), y)


def make_headers_map(headers):
    """
    all header-fields are joined here! This is against:  RFC 7230 and RFC 6265 (Coockies)
    However: the final request will provide the original-headers-list. So this convenient is ok!
    """
    acc = defaultdict(list)
    for key, value in map(lambda xy: lowercase_key(unicode2(xy)), headers):
        acc[key].append(value)

    return {k: ",".join(v) for k, v in acc.items()}


def serialize_headers(response):
    headers = response.get("headers", {})
    cookies = response.get("cookies", {})
    return [(k.encode("utf-8"), v.encode("utf-8")) for k, v in chain(headers.items(), cookies.items())]


async def consume_body(receive):
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    return body


async def responde_client(send, response):
    streaming = response.get("stream")
    if not streaming:
        await _responde_client_direct(send, response)
    else:
        await _responde_client_chunked(send, response)


async def _responde_client_chunked(send, response):
    status = response["status"]
    headers = serialize_headers(response)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    bytestream = response["stream"]
    async for chunk in bytestream:
        await send({"type": "http.response.body", "body": chunk, "more_body": True})
    await send({"type": "http.response.body", "body": b"", "more_body": False})


async def _responde_client_direct(send, response):
    status = response["status"]
    headers = serialize_headers(response)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send(
        {"type": "http.response.body", "body": response.get("body", b""), "more_body": False,}
    )


async def noop(receive, send):
    return None


async def _default_on_start(scope):
    pass


async def _default_on_stop(scope):
    pass


async def lifespan_handler(context, on_start, on_stop, receive, send):
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            user_config = {}
            try:
                user_config = await on_start(context)
                await send({"type": "lifespan.startup.complete"})
            except Exception as error:
                await send({"type": "lifespan.startup.failed", "message": str(error)})
                raise
            finally:
                _mark_startup_completed(user_config)

        elif message["type"] == "lifespan.shutdown":
            try:
                await on_stop(context)
                await send({"type": "lifespan.shutdown.complete"})
                return
            except Exception as error:
                await send({"type": "lifespan.shutdown.failed", "message": str(error)})
                raise


async def handle_request(context, handler, max_responde_timeout_s, max_receive_timeout_s, receive, send):
    headers_list = context.get("headers", [])
    headers = make_headers_map(headers_list)
    body = await wait_for(consume_body(receive), max_receive_timeout_s) if not context["type"] == "websocket" else b""
    method = context.get("method") if not context["type"] == "websocket" else "WS"
    request = {
        **context,
        "headers": headers,
        "body": body,
        "headers_list": headers_list,
        "method": method,
    }

    response = await handler(request)
    if callable(response):
        await response(receive, send)
    else:
        await wait_for(responde_client(send, response), max_responde_timeout_s)
    if __pytest__:
        return response


def build_server(
    handler, max_responde_timeout_s=30, max_receive_timeout_s=15, on_start=_default_on_start, on_stop=_default_on_stop
):
    async def wait_on_startup_then_run(func, receive, send):
        await _wait_on_completed_startup()
        _ring_state["user_config"]

        return await func(receive, send)

    _reset_ring_state()

    def request_start(scope):

        if "type" not in scope:
            raise NotImplementedError("no type in scope! error for %s" % scope)

        context = scope.copy()
        context["config"] = _ring_state["user_config"]

        request_handler = partial(handle_request, context, handler, max_responde_timeout_s, max_receive_timeout_s)

        if context["type"] in {"http", "websocket"} and _is_startup_completed():
            return request_handler

        elif context["type"] in {"http", "websocket"} and not _is_startup_completed():
            logging.warning(
                "Server processed request before start-up complete. This is against asgi-specification!"
                + "Wait until start-up is done!"
            )
            return partial(wait_on_startup_then_run, request_handler)

        elif context["type"] == "lifespan":
            _init_startup()
            return partial(lifespan_handler, context, on_start, on_stop)
        else:
            logging.warning(f"scope:type: {context['type']} currently not supported")
            return noop

    return request_start
