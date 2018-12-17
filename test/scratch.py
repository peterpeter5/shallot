from toolz import compose
from functools import reduce, partial


def mid1(next_middleware):
    print(f"mid1 initialized with {next_middleware}")
    def inner(handler, request):
        print("mid1")
        return next_middleware(handler, request)
    return inner


def mid2(next_middleware):
    print(f"mid2 initialized with: {next_middleware}")
    def inner(handler, request):
        print("mid2")
        return next_middleware(handler, request)
    return inner


def apply_middleware(*middlewares):
    """
    :param middlewares: middleware-functions to use with pyredux
    :return: wrapper-function to use with create_store
    """
    def _wrap_handler(handler):
        print("compose")
        call_chain =  middlewares
        chained_dispatcher = compose(*call_chain)(lambda _handler, request: _handler(request))
        print("chain composed")
        return partial(chained_dispatcher, handler)
    return _wrap_handler 



if __name__ == "__main__":
    server = apply_middleware(mid1, mid2)(lambda req: print("Default Handler: ", req))
    print("Result of request: ", server("Request"))