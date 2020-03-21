import aiofiles
import json as pyjson


def respond404(message="Not Found"):
    return text(message, status=404)


def respond400(message=""):
    return text(message, status=400)


def respond_not_modified(headers):
    msg = b"Not Modified"
    headers["content-length"] = str(len(msg))
    return {"status": 304, "body": msg, "headers": headers}


def filestream(path, headers=None, chunk_size=4096):
    headers = {} if headers is None else headers

    async def streamer():
        async with aiofiles.open(path, "rb") as afile:
            while True:
                content = await afile.read(chunk_size)
                yield content
                if len(content) < chunk_size:
                    break

    return {"status": 200, "body": b"", "stream": streamer(), "headers": headers}


def text(body="", status=200, encoding="utf-8"):
    transfered_body = body.encode(encoding)
    return {
        "status": status,
        "body": transfered_body,
        "headers": {"content-type": f"text/plain; charset={encoding}", "content-length": f"{len(transfered_body)}",},
    }


def json(data, status=200):
    transfer_body = pyjson.dumps(data).encode()
    return {
        "status": 200,
        "body": transfer_body,
        "headers": {"content-type": "application/json; charset=utf-8", "content-length": f"{len(transfer_body)}",},
    }


# -------------- WEBSOCKET - FUNCS ------------------------------------


def ws_send(data):
    if not isinstance(data, (str, bytes)):
        raise TypeError(f"Can NOT send data of type: {type(data)}! Possible types are: [bytes | str].")
    key = "text" if isinstance(data, str) else "bytes"
    return {key: data, "type": "websocket.send"}


def ws_close(code=1000):
    if not isinstance(code, int):
        raise TypeError(f"The exit code must be <int>. But not {type(code)}!")
    return {"type": "websocket.close", "code": code}


def ws_accept(subprotocol=None):
    return {"type": "websocket.accept", "subprotocol": subprotocol}
