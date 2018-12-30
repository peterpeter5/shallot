import os
import inspect
import pytest
from shallot.middlewares.staticfiles import wrap_static
from shallot.middlewares import apply_middleware


unhandled = {"status": 218, "body": b""}
__here__ = os.path.dirname(__file__)
valid_path = "/testxt"

valid_source = os.path.join(__here__, "data", valid_path.lstrip("/"))
valid_link_name = "linked.txt"
valid_link = os.path.join(__here__, "data", valid_link_name)


@pytest.fixture
def linked_file():
    os.symlink(valid_source, valid_link)
    assert os.path.exists(valid_link) and os.path.isfile(valid_link), "Wrong test setup"

    yield "/" + valid_link_name
    os.unlink(valid_link)


@pytest.fixture
def staticfiles_handler():
    return apply_middleware(wrap_static("./data", __here__))(noop_handler)


async def noop_handler(request):
    return unhandled


def test_wrap_static_is_middleware():
    request_handler = wrap_static(os.path.join(__here__, "data"))(noop_handler)
    assert inspect.isfunction(request_handler)


@pytest.mark.asyncio
async def test_static_middleware_does_nothing_on_other_than_get_head(staticfiles_handler):
    responses = [await staticfiles_handler({"method": meth, "path": valid_path}) for meth in ["POST", "PUT", "OPTIONS"]]
    assert len(responses) > 0
    for response in responses:
        assert unhandled is response


@pytest.mark.asyncio
async def test_static_middleware_does_404_on_double_dotted_paths(staticfiles_handler):
    response = await staticfiles_handler({"method": "GET", "path": valid_path + "../"})
    assert response["status"] == 404


@pytest.mark.asyncio
async def test_valid_requests_get_handled_with_streaming_response(staticfiles_handler):
    response = await staticfiles_handler({"method": "GET", "path": valid_path})
    assert response["status"] == 200
    assert response["body"] == b""
    assert response["stream"], "Found no stream!"


@pytest.mark.asyncio
async def test_static_response_have_caching_headers(staticfiles_handler):
    response = await staticfiles_handler({"method": "GET", "path": valid_path})
    assert "last-modified" in response["headers"]
    assert "etag" in response["headers"]


@pytest.mark.asyncio
@pytest.mark.xfail  # This is a planned feature, but its complex. FIXME later
async def test_by_default_sym_links_are_forbidden(staticfiles_handler, linked_file):
    response = await staticfiles_handler({"method": "GET", "path": linked_file})
    assert response["status"] == 404
