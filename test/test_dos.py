import pytest
import asyncio
from shallot.ring import build_server
from asyncio import TimeoutError


async def noop_sender(x):
    pass


async def noop_receive():
    return {"body": b""}


@pytest.mark.asyncio
async def test_slow_body_request():
    def slow_body_reader(timeout_s):
        async def slow_body():
            await asyncio.sleep(timeout_s)
            return {
                "body": b"body content.",
                "more_body": True
            }
        return slow_body

    handle_http = build_server(lambda x, y: 1, max_receive_timeout_s=0.2)

    with pytest.raises(TimeoutError):
        await handle_http({"type": "http"})(slow_body_reader(0.1), noop_sender)

    with pytest.raises(TimeoutError):
        await handle_http({"type": "http"})(slow_body_reader(1.1), noop_sender)


@pytest.mark.asyncio
async def test_slow_body_receiver():
    async def noop_handler(request):
        return {"status": 200, "body": b"asdf"}

    def slow_body_receiver(timeout_s):
        async def slow_body(x):
            await asyncio.sleep(timeout_s)

        return slow_body

    handle_http = build_server(noop_handler, max_responde_timeout_s=0.1)

    with pytest.raises(TimeoutError):
        await handle_http({"type": "http"})(noop_receive, slow_body_receiver(0.9))
