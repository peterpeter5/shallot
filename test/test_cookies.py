from shallot.middlewares.cookies import CookieSerializer, make_morsel_from_description, wrap_cookies
from shallot.middlewares import apply_middleware
from shallot.ring import serialize_headers
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


async def return_cookie_values_from_handler(handler, request=None):
    request = {} if request is None else request
    http_handler = apply_middleware(wrap_cookies)(handler)
    response = await http_handler(request)
    values = list(map(lambda x: x[1], response["cookies"].items()))
    return values


@pytest.mark.asyncio
async def test_expires_date_can_be_given_as_string_and_will_be_used_as_such():
    async def expires_string_cookie(req):
        return {"cookies": {"s": {"value": 3.4, "expires": "nonsense-string"}}}
    values = await return_cookie_values_from_handler(expires_string_cookie)
    assert len(values) == 1
    assert values == [
        "s=3.4; expires=nonsense-string"
    ]


@pytest.mark.asyncio
async def test_expires_date_as_number_will_be_converted_to_string():
    async def expires_int_float_cookie(req):
        return {"cookies": {"s": {"value": 3.4, "expires": 1545335438.5059335}}}
    values = await return_cookie_values_from_handler(expires_int_float_cookie)
    assert len(values) == 1
    assert values == [
        "s=3.4; expires=Thu, 20 Dec 2018 19:50:38 GMT"
    ]


@pytest.mark.asyncio
async def test_cookies_get_unset_when_descr_is_None():
    async def unset_one_set_one_new_cookie(req):
        return {"cookies": {"t": None, "a": {"value": "zt"}}}
    values = await return_cookie_values_from_handler(unset_one_set_one_new_cookie)
    assert len(values) == 2
    assert set(values) == {
        "t=; expires=Thu, 20 Dec 2018 19:50:38 GMT",
        "a=zt"
    }


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_all_request_cookies_get_unset_when_response_sets_cookies_to_none():
    """
    originally implemented as feature... At the moment i dont think it makes sense.
    it would suggest, that one can unset ALL cookies with just returning None. But thats only 
    true for cookies from the same route... I think a removal via explicit setting the cookie-name: None should
    be prefered. Although the complete feature might go away...
    """

    async def unset_all_request_cookies(request):
        return {
            "cookies": None
        }
    request_with_cookies = {"headers": {"cookie": "mu=choo; du=voo"}}
    values = await return_cookie_values_from_handler(unset_all_request_cookies, request_with_cookies)
    assert len(values) == 2
    assert set(values) == {
        "mu=; expires=Thu, 20 Dec 2018 19:50:38 GMT",
        "du=; expires=Thu, 20 Dec 2018 19:50:38 GMT"
    }
