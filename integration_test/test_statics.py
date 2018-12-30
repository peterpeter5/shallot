from hypothesis import given, settings
from hypothesis import strategies as st
import pytest
import os
from shallot.ring import build_server
from shallot.middlewares import apply_middleware
from shallot.middlewares.staticfiles import wrap_static
from multiprocessing import Process
import uvicorn
import requests
import time
import sys
import string
from random import randint, sample
from tempfile import NamedTemporaryFile, TemporaryDirectory
import os
from urllib.parse import quote


encoding = sys.getfilesystemencoding()

__here__ = os.path.dirname(__file__)
__test_data__ = "../test/data"

@pytest.fixture
def running_server():
    handler = apply_middleware(wrap_static(__test_data__, __here__))(noop_handler)
    server = build_server(handler)
    ip_port = ("127.0.0.1", 8550)
    process = Process(target=lambda: uvicorn.run(server, *ip_port))
    process.start()
    time.sleep(1)
    yield f"http://{ip_port[0]}:{ip_port[1]}/"
    process.terminate()
    time.sleep(1)

# ------ rfc1738 definitions --------------
alpha = string.ascii_letters
digits = string.digits
safe = "$-_.+"

st_unreserved = st.text(alphabet=alpha) | st.text(alphabet=digits) | st.text(alphabet=safe)
st_escape = st.from_regex(r"^%[0-9a-fA-F]{2}$")
st_uchar = st_unreserved | st_escape

st_hsegment = st_uchar | st.text(alphabet=";:@&=")
st_hpath_list = st.lists(st_hsegment)

# -------------------------------------------

async def noop_handler(request):
    return {"status": 218}


@given(st.text())
def test_arbitrary_text_does_not_result_in_500(running_server, path):
    result = requests.get(running_server + path)
    assert result.status_code in {200, 218}, f"{result}, {result.content}"


@given(st_hpath_list)
def test_hpath(running_server, http_path):
    http_path = "/".join(http_path)
    result = requests.get(running_server + http_path)
    assert result.status_code in {200, 218, 404}, f"{result}, {result.content}"


def is_url_encodeable(path_name):
    try:
        path_name = path_name.decode(encoding) if isinstance(path_name, bytes) else path_name
        quoted = quote(path_name)

        return not ("?" in path_name or "#" in path_name or "/" in path_name or "\x00" in path_name)
    except Exception:
       return False 


@given(path=st.text().filter(is_url_encodeable), content=st.binary(min_size=0, max_size=10*6))
@settings(max_examples=500)
def test_all_urlencodeable_filenames_can_be_served_via_statics(running_server, path, content):
    if isinstance(path, bytes):
        path = path.decode(encoding)

    base_dir, fname = os.path.split(path)
    statics_folder = os.path.join(__here__, __test_data__)
    random_string = content
    
    with NamedTemporaryFile(dir=os.path.join(statics_folder, base_dir), prefix=fname) as tfile:
        tfile.write(random_string)
        tfile.flush()
        _, actual_fname = os.path.split(tfile.name)
        result = requests.get(running_server + os.path.join(base_dir, actual_fname))
        assert result.status_code == 200, f"File not found, {result}, {result.content}, {result.url}"
        assert result.content == random_string, f"File not found, {result}, {result.content}, {result.url}"
