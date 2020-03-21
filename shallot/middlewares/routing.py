from collections import defaultdict
import re


class RPartial:
    __slots__ = ("func", "args")

    def __init__(self, func, args):
        self.func = func
        self.args = args

    def __call__(self, *args, **kwargs):
        return self.func(*(args + self.args), **kwargs)

    def __repr__(self):
        self.__str__()

    def __str__(self):
        return f"partial-func: <{self.func}> + args: {self.args}"


def map_over_routes(func, routing_table):
    return map(lambda entry: (func(entry[0]), *entry[1:]), routing_table)


def remove_trailing_slashes_from_routing_table(routing_table):
    return map_over_routes(lambda route: route.rstrip("/"), routing_table)


def lowercase_all_routes(routing_table):
    return map_over_routes(lambda route: route.lower(), routing_table)


def build_static_router(routing_table):
    static_routs = list(filter(lambda entry: "{" not in entry[0], routing_table))
    static_router = {}
    for route, methods, dispatch in static_routs:
        methods_before = static_router.get(route, {})
        new_methods = {meth: dispatch for meth in methods}
        static_router[route] = {**methods_before, **new_methods}
    return static_router


def build_dynamic_router(routing_table):
    dynamic_routes = list(filter(lambda entry: "{" in entry[0], routing_table))
    dyn_router = defaultdict(dict)
    for route, methods, dispatch in dynamic_routes:
        regex_path = re.sub(r"\{(.+)\}", "(.*)", route)
        num_slashes = route.count("/")
        old_methods = dyn_router.get(num_slashes, {}).get(regex_path, {})
        new_methods = {meth: dispatch for meth in methods}
        dyn_router[num_slashes].update({regex_path: {**old_methods, **new_methods}})
    return dyn_router


def router(routing_table):
    routing_table = list(remove_trailing_slashes_from_routing_table(routing_table))
    static_router = build_static_router(routing_table)
    dynamic_router = build_dynamic_router(routing_table)

    def dispatch(request):
        path = request["path"].rstrip("/")
        method = request["method"]
        try:
            return static_router[path][method], tuple()
        except KeyError:
            regex_matchers = dynamic_router.get(path.count("/"))
            if not regex_matchers:
                return None, None
            for possible, extra_info in regex_matchers.items():
                match = re.fullmatch(possible, path)
                if match and method in extra_info:
                    return extra_info[method], match.groups()
            else:
                return None, None

    return dispatch


def wrap_routes(routing_table):
    _router = router(routing_table)

    def wrap_middleware(next_middleware):
        async def dispatch_handler(handler, request):
            new_handler, args = _router(request)
            if new_handler is None:
                return await next_middleware(handler, request)
            else:
                return await next_middleware(RPartial(new_handler, args), request)

        return dispatch_handler

    return wrap_middleware
