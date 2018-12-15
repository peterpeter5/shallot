import pytest
from aring.middlewares.content_type import wrap_content_type


@pytest.fixture
def content_type():
    return wrap_content_type()


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
async def test_content_types_are_guessed_for_known_extensions(content_type):
    async def no_content_type_handler(request):
        return {"status": 200}

    response = await content_type(no_content_type_handler)({"path": "some/path/t.txt"})
    assert response["headers"]["content-type"] == "text/plain"