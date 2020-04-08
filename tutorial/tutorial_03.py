from shallot import build_server, websocket, standard_not_found
from shallot.middlewares import wrap_routes, apply_middleware
from shallot.response import ws_send


@websocket
async def echo_server(request, receiver):
    async for message in receiver:
        yield ws_send(f"@echo: {message}")


@websocket
async def print_out_server(request, receiver):
    async for message in receiver:
        print(message)
        if message == "exit":
            raise Exception("Boom")


routes = [
    ("/echo", ["WS"], echo_server),
    ("/print-out", ["WS"], print_out_server)

]

app = build_server(
    apply_middleware(
        wrap_routes(routes)
    )(standard_not_found)
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)