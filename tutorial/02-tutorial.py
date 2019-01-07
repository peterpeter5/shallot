from shallot import build_server
from shallot.response import text, json
from shallot.middlewares import apply_middleware, wrap_json, wrap_routes


async def not_found(request):
    return text("Not Found", 404)

fruit_store = {
    "oranges": {"descr": "an orange ball", "qty": 0, "name": "orange"}, 
    "apples": {"descr": "an green or red ball", "qty": 0, "name": "apple"}
}


async def fruit_collection(request):
    return json({"fruits": list(fruit_store.keys())})


async def fruit_details(request, fruit_name):
    return json(fruit_store[fruit_name])

routes = [
    ("/fruits", ["GET"], fruit_collection),
    ("/fruits/{name}", ["GET"], fruit_details)
]


middlewares = apply_middleware(
    wrap_json,
    wrap_routes(routes)
)
fruit_app = build_server(middlewares(not_found))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fruit_app, "127.0.0.1", 5000, debug=True)
