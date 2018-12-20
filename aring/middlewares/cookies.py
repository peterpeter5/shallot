from http.cookies import SimpleCookie, CookieError, Morsel
from urllib.parse import quote

def make_morsel_from_description(name, descr):
    m = Morsel()
    value = str(descr.pop("value"))
    m.set(name, value, quote(value))
    for option, value in descr.items():
        m[option] = value
    return m


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
            cookies = {k:v.value for k, v in c.items()}
        else:
            cookies = None

        request["cookies"] = cookies        
        response = await next_middleware(handler, request)
        
        response_cookies = CookieSerializer(
            make_morsel_from_description(name, descr) 
            for name, descr in response.get("cookies", {}).items())
        response["cookies"] = response_cookies
        return response

    return cookies