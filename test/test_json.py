import pytest
from shallot.middlewares import apply_middleware
from shallot.middlewares.json import wrap_json


@pytest.fixture
def json_middleware():
    return apply_middleware(wrap_json)


@pytest.mark.asyncio
async def test_json_header_results_auto_parsed_json_key(json_middleware):
    async def noop(request):
        return request

    request = {
        "headers": {"content-type": "application/json"},
        "body": b'{"a": 1}'
    }
    response = await json_middleware(noop)(request)
    assert "json" in response
    assert response["json"] == {"a": 1}


@pytest.mark.asyncio
async def test_without_json_header_json_key_will_be_none(json_middleware):
    async def noop(request):
        return request

    request = {
        "headers": {"content-type": "text/plain"},
        "body": b'{"a": 1}'
    }
    response = await json_middleware(noop)(request)
    assert "json" in response
    assert response["json"] == None


@pytest.mark.asyncio
async def test_a_malformed_json_results_in_400_reponse(json_middleware):
    async def noop(request):
        return request

    request = {
        "headers": {"content-type": "application/json"},
        "body": b'{"a": 1LO}'
    }
    response = await json_middleware(noop)(request)
    assert 400 == response["status"]
