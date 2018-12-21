from aring.middlewares.cookies import CookieSerializer, make_morsel_from_description, wrap_cookies
from aring.middlewares import apply_middleware
from aring.ring import serialize_headers
import pytest

cookie_values = {
    "session": {
        "value": 12, 
        "secure": True,
        "path": "/zuze",
        "domain": "asdf.purzel.com",
        "max-age": 12*34,
        "version": 4,
        "httponly": True 
        },
    "apple": {"value": "quick"}
}

@pytest.fixture
def cookie_handler():
    async def noop(request):
        return {
            "request_cookies": request.get("cookies"),
            "cookies": {"a": {"value": "tasty_tomato"}, "b": {"value": 12, "secure": True}}
        }
    return apply_middleware(wrap_cookies)(noop)


def test_header_serializer_with_headers_and_cookies():
    response = {
        "headers": {"content-type": "text/plain", "Y-X": "123"},
        "cookies": CookieSerializer(
            make_morsel_from_description(name, descr)
            for name, descr in {"a": {"value": "cherry"}, "b": {"value": 12}}.items()
        )
    }
    headers_list = serialize_headers(response)
    assert headers_list == [
        (b"content-type", b"text/plain"),
        (b"Y-X", b"123"),
        (b"Set-Cookie", b"a=cherry"),
        (b"Set-Cookie", b"b=12"),
    ]

    
def test_cookie_serializer():
    cs = CookieSerializer(
        make_morsel_from_description(name, descr)
        for name, descr in cookie_values.items()
    )
    header_list = list(cs.items())
    assert len(header_list)
    for header_name, value in header_list:
        assert header_name == "Set-Cookie"
        assert value in {
            "apple=quick",
            "session=12; Domain=asdf.purzel.com; HttpOnly; Max-Age=408; Path=/zuze; Secure; Version=4"
        }


@pytest.mark.asyncio
async def test_cookie_header_get_parsed_to_dict(cookie_handler):
    response = await cookie_handler({"headers": {"cookie": "yummy_cookie=choco; tasty_cookie=strawberry"}})
    assert isinstance(response["request_cookies"], dict)


@pytest.mark.asyncio
async def test_cookie_response_dict_becomes_cookie_serializer(cookie_handler):
    response = await cookie_handler({"headers": {"cookie": "yummy_cookie=choco; tasty_cookie=strawberry"}})
    assert isinstance(response["cookies"], CookieSerializer)
    values = list(map(lambda x: x[1], response["cookies"].items()))
    assert len(values) == 2
    assert set(values) == {
        "a=tasty_tomato", "b=12; Secure"
    }


@pytest.mark.asyncio
async def test_expires_date_can_be_given_as_string_and_will_be_used_as_such():
    async def expires_string_cookie(req):
        return {"cookies": {"s": {"value": 3.4, "expires": "nonsense-string"}}}
    http_handler = apply_middleware(wrap_cookies)(expires_string_cookie)
    response = await http_handler({})
    values = list(map(lambda x: x[1], response["cookies"].items()))
    assert len(values) == 1
    assert values == [
        "s=3.4; expires=nonsense-string"
    ]


@pytest.mark.asyncio
async def test_expires_date_as_number_will_be_converted_to_string():
    async def expires_int_float_cookie(req):
        return {"cookies": {"s": {"value": 3.4, "expires": 1545335438.5059335}}}
    http_handler = apply_middleware(wrap_cookies)(expires_int_float_cookie)
    response = await http_handler({})
    values = list(map(lambda x: x[1], response["cookies"].items()))
    assert len(values) == 1
    assert values == [
        "s=3.4; expires=Thu, 20 Dec 2018 19:50:38 GMT"
    ]