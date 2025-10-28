from .helper import running_sever_fixture
from shallot.middlewares import wrap_routes, apply_middleware
from shallot.response import text
from shallot import build_server
from hypothesis import given, settings
from hypothesis import strategies as st
import requests


async def _not_found(request):
    raise AssertionError()


async def _static_route(request):
    return text(request["path"])


async def _dynamic_route(request, url_paramerter):
    return text(f"{request['path']}:{url_paramerter}")

route = [
    ("/just/a/route", ["GET"], _static_route),
    ("/route/", ["GET"], _static_route),
    ("/route/{ends}", ["GET"], _dynamic_route),
    ("/route/{in_the_middle}/dyn", ["POST"], _dynamic_route),
]

handler = apply_middleware(wrap_routes(route))(_not_found)
_server = build_server(handler)

running_server = running_sever_fixture(_server)


def test_static_route(running_server):

    result = requests.get(running_server + "/just/a/route")
    assert result.status_code == 200, f"{result}, {result.content}"
    assert result.content == b"/just/a/route"

    result = requests.get(running_server + "/just/a/route/")
    assert result.status_code == 200, f"{result}, {result.content}"
    assert result.content == b"/just/a/route/"


@given(st.text(min_size=1).filter(lambda text: not any(map(lambda x: x in text, "/:#?\n"))))
def test_dynamic_routes_at_the_end(running_server, dynamic_text):
    target_url_path = f"/route/{dynamic_text}"
    result = requests.get(running_server + target_url_path)
    assert result.status_code == 200, f"{result}, {result.content}"
    url, parameter = result.content.decode().split(":")
    assert url == target_url_path
    assert parameter == dynamic_text

