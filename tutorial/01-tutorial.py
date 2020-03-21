from shallot import build_server
from shallot.response import text
from shallot.middlewares import apply_middleware, wrap_static, wrap_content_type


async def greetings(request):
    user_agent = request["headers"].get("user-agent")
    return text(f"Special greetings to you: {user_agent}")


middlewares = apply_middleware(
    wrap_content_type(),
    wrap_static("./static"),
    
)

greet_and_static_handler = middlewares(greetings)

hello_world_app = build_server(greet_and_static_handler)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(hello_world_app, host="127.0.0.1", port=5000, debug=True)
