from collections import defaultdict
from shallot.response import filestream
from asyncio import wait_for
import sys
from itertools import chain
from functools import partial
import logging

__pytest__ = hasattr(sys, "_pytest_shallot_")


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

    return {
        k: ",".join(v) for k, v in acc.items()
    }


def serialize_headers(response):
    headers = response.get("headers", {})
    cookies = response.get("cookies", {})
    return [
        (k.encode("utf-8"), v.encode("utf-8"))
        for k, v in chain(headers.items(), cookies.items())
    ]


async def consume_body(receive):
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return body


async def responde_client(send, response):
    streaming = response.get("stream")
    if not streaming:
        await _responde_client_direct(send, response)
    else:
        await _responde_client_chunked(send, response)


async def _responde_client_chunked(send, response):
    status = response['status']
    headers = serialize_headers(response)
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers
    })
    bytestream = response['stream']
    async for chunk in bytestream:
        await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
    await send({'type': 'http.response.body', 'body': b'', 'more_body': False})


async def _responde_client_direct(send, response):
    status = response['status']
    headers = serialize_headers(response)
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers
    })
    await send({
        'type': 'http.response.body',
        'body': response.get("body", b''),
        "more_body": False,
    })


async def noop(receive, send):
    return None


def build_server(handler, max_responde_timeout_s=30, max_receive_timeout_s=15):
    def request_start(context):
        async def handle_handler(receive, send):
            headers_list = context.get('headers', [])
            headers = make_headers_map(headers_list)
            body = await wait_for(consume_body(receive), max_receive_timeout_s) if not context["type"] == "websocket" else b""
            method = context.get("method") if not context["type"] == "websocket" else "WS"
            request = {
                **context,
                "headers": headers, 
                'body': body, 
                'headers_list': headers_list,
                "method": method
            }

            response = await handler(request)
            if callable(response):
                await response(receive, send)
            else:
                await wait_for(responde_client(send, response), max_responde_timeout_s)
            if __pytest__:
                return response

        if "type" not in context:
            raise NotImplementedError("no type in scope! error for %s" % context)
        if context["type"] in {"http", "websocket"}:
            return handle_handler
        else:
            logging.warn(f"scope:type: {context['type']} currently not supported")
            return noop
    return request_start
