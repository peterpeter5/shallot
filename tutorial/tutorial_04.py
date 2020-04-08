
import time
import asyncio
from shallot import websocket, standard_not_found, build_server
from shallot.response import ws_send
from shallot.middlewares import wrap_routes, apply_middleware


@websocket
async def fan_in(request, receiver):
    async for message in receiver:
        # do something usefull. For example print the data
        print(message)



@websocket
async def fan_out(request, receiver):
    while True:
        yield(ws_send(f"current-time-stamp {time.time()}"))
        await asyncio.sleep(1)


@websocket
async def one_to_one(request, receiver):
    async for message in receiver:
        if message == "hello":
            yield ws_send("hello beautiful")
        elif message == "exit":
            yield ws_send("byebye")
            break
        elif message == "i like you":
            yield ws_send("That is very nice! I like you too!")
        else:
            yield ws_send("pardon me. I do not have a reply to this")


routes = [
    ("/fan-in", ["WS"], fan_in),
    ("/fan-out", ["WS"], fan_out),
    ("/chatbot", ["WS"], one_to_one),

]


app = build_server(apply_middleware(
        wrap_routes(routes)
    )(standard_not_found))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)