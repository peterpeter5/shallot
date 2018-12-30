import pytest
from shallot.middlewares.content_type import wrap_content_type
from shallot.middlewares import apply_middleware


@pytest.fixture
def content_type():
    add_mapping = {"application/fruit": [".apple", "orange"]}
    return apply_middleware(wrap_content_type(additional_content_types=add_mapping))


@pytest.mark.asyncio
async def test_content_types_are_guessed_are_not_changed_if_provided(content_type):

    async def with_content_type_handler(request):
        return {"status": 200, "headers": {"content-type": "none/existing/content-type"}}

    response = await content_type(with_content_type_handler)({"path": "some/path/t.txt"})
    assert "none/existing/content-type" == response["headers"]["content-type"]


@pytest.mark.asyncio
async def test_content_types_for_none_streaming_and_non_guessable_responses_is_octet_stream(content_type):
    async def no_content_type_handler(request):
        return {}

    response = await content_type(no_content_type_handler)({"path": "some/path/t/no/extension"})
    assert "application/octet-stream" == response["headers"]["content-type"]


@pytest.mark.asyncio
async def test_content_types_for_streaming_without_known_ext_is_octeat(content_type):
    async def stream_handler(request):
        return {"stream": "asf"}

    response = await content_type(stream_handler)({"path": "some/path/t/no/extension"})
    assert "application/octet-stream" == response["headers"]["content-type"]


@pytest.mark.asyncio
async def test_default_content_types_for_unknown_ext_can_be_overridden():
    async def stream_handler(request):
        return {"stream": "asf"}
    content_type = apply_middleware(wrap_content_type(default_content_type="app/buba"))
    response = await content_type(stream_handler)({"path": "some/path/t/no/extension"})
    assert "app/buba" == response["headers"]["content-type"]


@pytest.mark.asyncio
async def test_content_types_are_guessed_for_known_extensions(content_type):
    async def no_content_type_handler(request):
        return {"status": 200}

    response = await content_type(no_content_type_handler)({"path": "some/path/t.txt"})
    assert response["headers"]["content-type"] == "text/plain"


@pytest.mark.asyncio
async def test_content_type_mappings_added_are_honored_even_when_no_dot_was_provided(content_type):
    async def no_content_type_handler(request):
        return {"status": 200}

    response = await content_type(no_content_type_handler)({"path": "some/path/t.apple"})
    assert response["headers"]["content-type"] == "application/fruit"

    response = await content_type(no_content_type_handler)({"path": "some/path/t.orange"})
    assert response["headers"]["content-type"] == "application/fruit"
