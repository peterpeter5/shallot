import inspect
import pytest
from aring.ring import build_server



async def receive_none():
    return {'more_body': False}


async def send_none(x):
    print(x)

async def handler_identity(x):
    return {"status": 200, **x}

def test_ring_server_yields_function():
    server = build_server(lambda x: x)
    assert inspect.isfunction(server)


def test_server_func_returns_handler_func_for_request():
    server = build_server(lambda x: x)
    handler_func = server({})
    assert inspect.isfunction(handler_func)


@pytest.mark.asyncio
async def test_server_coerces_header_list_into_dict():
    headers = [(b"a", b"asdff"), (b"ccccccccc"*1024, b"zu777/&!&/"), (b"double", b"123"), (b"double", b"asdf")]
    server = build_server(handler_identity)
    handler_func = server({"headers": headers})
    result = await handler_func(receive_none, send_none)
    assert {"a": "asdff", "ccccccccc"*1024: "zu777/&!&/", "double": "123,asdf"} == result['headers']

@pytest.mark.asyncio
async def test_server_has_no_problems_with_empty_headers():
    server = build_server(handler_identity)
    handler_func = server({})
    result = await handler_func(receive_none, send_none)
    assert {} == result['headers']