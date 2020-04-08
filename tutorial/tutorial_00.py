from shallot import build_server
from shallot.response import text


async def greetings(request):
    user_agent = request["headers"].get("user-agent")
    return text(f"Special greetings to you: {user_agent}")

    
hello_world_app = build_server(greetings)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(hello_world_app, host="127.0.0.1", port=5000, debug=True)
