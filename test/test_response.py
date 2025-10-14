from shallot.response import filestream, text, json as json_response
import inspect
import os
import pytest
from tempfile import NamedTemporaryFile


__here__ = os.path.dirname(__file__)


def test_filestream_returns_empty_body_and_stream():
    fs_response = filestream("not/existing/file.txt")
    assert fs_response["body"] == b''
    assert inspect.isasyncgen(fs_response["stream"])


@pytest.mark.asyncio
async def test_filestream_stream_contains_all_bytes():
    existing_path = os.path.join(__here__, "data", "testxt")
    fs = filestream(existing_path)
    b_content = b"".join([c async for c in fs["stream"]])
    with open(existing_path, "rb") as testfile:
        expected_content = testfile.read()
    assert expected_content == b_content


@pytest.mark.asyncio
async def test_filestream_response_will_fail_on_consmution_not_before():
    fs_response = filestream("not/existing/file.txt")
    with pytest.raises(FileNotFoundError):
        async for i in fs_response["stream"]:
            print(i)


@pytest.mark.asyncio
async def test_filestream_reads_all_bytes_chunked():
    for size in [0, 1, 1024, 4095, 4096, 4098, 4098*5 + 3]:
        with NamedTemporaryFile() as temp:
            content = b'\x09' * size
            temp.write(content)
            temp.flush()
            fs = filestream(temp.name)
            actual = b''
            async for chunk in fs['stream']:
                actual += chunk

            assert actual == content, f"Len of actual: <{len(actual)}> and of content <{len(content)}> "


def test_json_response_honors_status_code():
    response = json_response({"any": "data"}, status=499)
    assert response["status"] == 499, "Status Code not properly set!"


def test_json_response_is_utf_8_decoded():
    emoji = b"\xF0\x9F\x98\x81".decode("utf-8")
    response = json_response([emoji], ensure_ascii=False)
    assert response["body"].decode("utf-8") == f'["{emoji}"]'


def test_json_response_encoding_is_properly_set():
    test_string = "Äshallot!"
    target = test_string.encode("ISO-8859-1")
    response = json_response([test_string], encoding="ISO-8859-1", ensure_ascii=False)
    assert response["body"].strip(b'["]') == target

    assert response["headers"]["content-type"] == "application/json; charset=ISO-8859-1"


def test_text_response_honors_status_code():
    response = text("any string", status=499)
    assert response["status"] == 499, "Status Code not properly set!"


def test_json_response_is_utf_8_decoded():
    emoji = b"\xF0\x9F\x98\x81".decode("utf-8")
    response = text(emoji)
    assert response["body"].decode("utf-8") == emoji


def test_json_response_encoding_is_properly_set():
    test_string = "Äshallot!"
    target = test_string.encode("ISO-8859-1")
    response = text(test_string, encoding="ISO-8859-1")
    assert response["body"] == target

    assert response["headers"]["content-type"] == "text/plain; charset=ISO-8859-1"

