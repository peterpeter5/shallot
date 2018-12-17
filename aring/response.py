import aiofiles


def responde404():
    return {"status": 404, "body": b"Not Found", "headers": {"content-type": "text/plain"}}


def responde_not_modified(headers):
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
        "headers": {
            "content-type": f"text/plain; charset={encoding}",
            "content-length": f"{len(transfered_body)}"

        }
    }