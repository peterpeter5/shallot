# flake8: noqa F401
from functools import partial, reduce
from .content_type import wrap_content_type
from .cookies import wrap_cookies
from .json import wrap_json
from .parameters import wrap_parameters
from .staticfiles import wrap_static
from .routing import wrap_routes


def _compose(*functions):
    """
    compose 2-N functions in a way that a function call of the composed
    function would end up like this:
        f_3(f_2(f_1(*args, **kwargs))))
    If you compose just 1 function the same function will be returned as a shortcut
    :param functions: functions you want to compose
    :return: composed functions
    """

    def compose_two_funcs(func1, func2):
        def _composition(*args, **kwargs):
            return func2(func1(*args, **kwargs))

        return _composition

    def composition(*args, **kwargs):
        funcs = reversed(functions)
        composed = reduce(compose_two_funcs, funcs)
        return composed(*args, **kwargs)

    if len(functions) == 1:
        return functions[0]

    return composition


def apply_middleware(*middlewares):
    """
    :param middlewares: middleware-functions to wrap-up 
    :return: wrapper-function to use with handler -> server
    """

    async def exectue_handler(_handler, request):
        return await _handler(request)

    def _wrap_handler(handler):
        call_chain = middlewares
        chained_dispatcher = _compose(*call_chain)(exectue_handler)
        return partial(chained_dispatcher, handler)

    return _wrap_handler
