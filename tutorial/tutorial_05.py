from shallot import websocket, build_server, standard_not_found
from shallot.middlewares import wrap_routes, apply_middleware
from shallot.response import json, text, ws_send
import asyncio


class BroadcastChannel:

    def __init__(self):
        self._event_log = []
        self._positions = {}

    def put(self, item):
        self._event_log.append(item)

    async def get(self, name):
        if name not in self._positions:
            self._positions[name] = 0

        subscriber_position = self._positions[name]
        while subscriber_position >= len(self._event_log):
            await asyncio.sleep(0.1)

        items = self._event_log[subscriber_position:]
        self._positions[name] = len(self._event_log)
        return items


_broadcast_channel = BroadcastChannel()


def send_broadcast(name, item):
    _broadcast_channel.put((name, item))


async def receive_from_broadcast(name):
    while True:
        items = await _broadcast_channel.get(name)
        foreign_msgs = list(filter(lambda name_msg: name_msg[0] != name, items))
        if foreign_msgs:
            for m in foreign_msgs:
                yield m 
        else:
            await asyncio.sleep(0.01)


async def named_receiver(name, receiver):
    while True:
        msg = await receiver.__anext__()
        yield name, msg


async def merge(*streams):
    async def _put_on_q(queue, stream):
        async for m in stream:
            await queue.put(m)
            
    q = asyncio.Queue()
    tasks = list(map(lambda s: _put_on_q(q, s), streams))
    for t in tasks:
        asyncio.ensure_future(t)
    while True:
        item = await q.get()
        yield item
 

@websocket
async def chatroom(scope, receiver, name):
    client_msgs = named_receiver(name, receiver)
    broadcast_messages = receive_from_broadcast(name)

    async for user_name, message in merge(client_msgs, broadcast_messages):
        if user_name == name:
            send_broadcast(name, message)
        else:
            yield ws_send(f"@{user_name}: {message}")


async def alive(request):
    return json({"alive": True})


app = build_server(
    apply_middleware(
        wrap_routes([
            ("/chat/{name}", ["WS"], chatroom),
            ("/", ["GET"], alive)
        ])
    )(standard_not_found)
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
