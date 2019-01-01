import pytest
from shallot.middlewares import apply_middleware
from shallot.middlewares.parameters import wrap_parameters


async def return_request(request):
    return request


@pytest.fixture
def parameters():
    return apply_middleware(wrap_parameters())(return_request)


@pytest.mark.asyncio
async def test_without_url_or_body_params_is_empty_dict(parameters):
    result = await parameters({})
    assert "params" in result
    assert result["params"] == {}


@pytest.mark.asyncio
async def test_url_query_string_gets_parsed_to_dict(parameters):
    result = await parameters({"query_string": "idx1=0&in=collection"})
    assert "params" in result
    expected = {"idx1": ["0"], "in": ["collection"]}
    assert result["params"] == expected
    assert result["query_params"] == expected
    assert result["form_params"] == {}


@pytest.mark.asyncio
async def test_url_query_string_gets_parsed_to_dict_bytes(parameters):
    result = await parameters({"query_string": b"idx1=0&in=collection"})
    assert "params" in result
    expected = {"idx1": ["0"], "in": ["collection"]}
    assert result["params"] == expected
    assert result["query_params"] == expected
    assert result["form_params"] == {}


@pytest.mark.asyncio
async def test_params_are_not_parsed_if_content_type_is_wrong(parameters):
    result = await parameters({"body": b"idx1=0&in=collection"})
    assert "params" in result
    assert result["params"] == {}
    assert result["query_params"] == {}
    assert result["form_params"] == {}


@pytest.mark.asyncio
async def test_params_are_parsed_if_content_type_is_right(parameters):
    result = await parameters({
        "body": b"id=%25&in=coll&in=world", 
        "headers": {"content-type": "application/x-www-form-urlencoded"}
    })
    assert "params" in result
    expected = {"id": ["%"], "in": ["coll", "world"]}
    assert result["params"] == expected
    assert result["query_params"] == {}
    assert result["form_params"] == expected



@pytest.mark.asyncio
async def test_form_and_query_params_can_be_mixed(parameters):
    result = await parameters({
        "query_string": "q=0&d=n",
        "body": b"id=%25&in=coll&in=world", 
        "headers": {"content-type": "application/x-www-form-urlencoded"}
    })
    assert "params" in result
    assert result["params"] == {"q": ["0"], "d": ["n"], "id": ["%"], "in": ["coll", "world"]}
    assert result["query_params"] == {"q": ["0"], "d": ["n"]}
    assert result["form_params"] == {"id": ["%"], "in": ["coll", "world"]}
