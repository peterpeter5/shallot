from shallot.middlewares.routing import build_static_router, router as _router
import pytest


sample_routing_table = [
    ("/", ["GET"], lambda x: "index"),
    ("/users", ["GET"], lambda x: "users"),
    ("/users/{uid}", ["GET", "POST"], lambda x, y: "users/uid/" + str(y)),
    ("/documents", ["GET"], lambda x: "docs - get"),
    ("/documents", ["POST", "PUT"], lambda x: "change docs"),
    ("/trailing/", ["POST", "GET"], lambda x: "route_with_trailing_slash"),
]


@pytest.fixture
def router():
    return _router(sample_routing_table)


def test_build_static_router_returns_dict():
    static_router = build_static_router(sample_routing_table)
    assert len(static_router["/"]) == 1
    assert "/users/{uid}" not in static_router
    assert set(static_router["/documents"]) == {"GET", "PUT", "POST"}


def test_router_return_correct_handler_for_given_static_path(router):
    handler, args = router({"path": "/", "method": "GET"})
    assert handler(None) == "index"
    assert args is tuple()


def test_router_return_correct_handler_for_given_static_path_ignoring_trailing_slashes(router):
    handler, args = router({"path": "/documents", "method": "GET"})
    assert handler(None) == "docs - get"
    assert args is tuple()

    handler, args = router({"path": "/documents/", "method": "GET"})
    assert handler(None) == "docs - get"
    assert args is tuple()


def test_trailing_slashes_from_routes_are_ignored(router):
    handler, args = router({"path": "/trailing", "method": "GET"})
    assert handler(None) == "route_with_trailing_slash"
    assert args is tuple()


def test_router_dispatches_to_dynamic_route(router):
    handler, args = router({"path": "/users/3", "method": "GET"})
    assert "users/uid/3" == handler(None, args[0])


def test_router_dispatches_to_dynamic_route_ignoring_trailing_slashes(router):
    handler, args = router({"path": "/users/3/", "method": "GET"})
    assert "users/uid/3" == handler(None, args[0])
