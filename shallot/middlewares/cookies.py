from http.cookies import SimpleCookie, CookieError, Morsel
from urllib.parse import quote
from wsgiref.handlers import format_date_time


def make_morsel_from_description(name, descr):
    m = Morsel()
    value = str(descr.pop("value"))
    m.set(name, value, quote(value))
    for option, value in descr.items():
        m[option] = value if option != "expires" else format_expiration_date(value)
    return m


def make_unset_morsel(name):
    m = Morsel()
    m.set(name, "", "")
    m["expires"] = format_expiration_date(1545335438.5059335)
    return m


def format_expiration_date(expires):
    if isinstance(expires, str):
        return expires
    elif isinstance(expires, (int, float)):
        return format_date_time(expires)
    else:
        raise TypeError(f"Dont know how to convert type <{type(expires)}> to time-header!")


class CookieSerializer:
    def __init__(self, morsels):
        self._morsels = morsels

    def items(self):
        return (m.output().split(": ") for m in self._morsels)


def wrap_cookies(next_middleware):
    async def cookies(handler, request):
        headers = request.get("headers", {})
        if "cookie" in headers:
            try:
                c = SimpleCookie(headers["cookie"])
            except CookieError:
                c = SimpleCookie("")
            cookies = {k: v.value for k, v in c.items()}
        else:
            cookies = {}

        request["cookies"] = cookies
        response = await next_middleware(handler, request)

        response_cookies = CookieSerializer(
            make_morsel_from_description(name, descr) if descr is not None else make_unset_morsel(name)
            for name, descr in response.get("cookies", {}).items()
        )
        response["cookies"] = response_cookies
        return response

    return cookies
