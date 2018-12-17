

def build_static_router(routing_table):
    static_routs = list(filter(lambda entry: "{" not in entry[0], routing_table))
    static_router = {}
    for route, methods, dispatch in static_routs:
        methods_before = static_router.get(route, {}) 
        new_methods = {
            meth: dispatch
            for meth in methods
        }
        static_router[route] = {
            **methods_before,
            **new_methods
            }
    return static_router


def router(routing_table):
    static_router = build_static_router(routing_table)
    def dispatch(request):
        path = request["path"]
        method = request["method"]
        handler = static_router[path][method]
        return handler

    return dispatch


def wrap_routes(routing_table):
    _router = router(routing_table)
    def wrap_middleware(next_middleware):
        async def dispatch_handler(handler, request):
            new_handler = _router(request)
            return await next_middleware(new_handler, request)
        return dispatch_handler
    return wrap_middleware