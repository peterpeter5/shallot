# flake8: noqa F401
from .ring import build_server
from .websocket import websocket, WSDisconnect
from . import response as _response


async def standard_not_found(request):
    async def _close_websocket(receive, send):
        msg = _response.ws_close()  # 4404 more or less 404 - not found?
        await send(msg)

    request_type = request.get("type")
    if request_type == "websocket":
        return _close_websocket
    else:
        return _response.respond404()
