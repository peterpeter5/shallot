from contextlib import contextmanager
from hypothesis import given, settings
from hypothesis import strategies as st
import pytest
import os
from shallot import build_server
from shallot.middlewares import apply_middleware
from shallot.middlewares.staticfiles import wrap_static
from multiprocessing import Process
import uvicorn
import requests
import time
import sys
import shutil
from random import randint, sample
from tempfile import NamedTemporaryFile, TemporaryDirectory
import os
from urllib.parse import quote, unquote
from .helper import running_sever_fixture, st_hpath_list
from shallot.middlewares import wrap_static



encoding = sys.getfilesystemencoding()

__here__ = os.path.dirname(__file__)
__test_data__ = "../test/data"
max_path_length = os.pathconf(__here__, 'PC_PATH_MAX')
max_filename_length = os.pathconf(__here__, 'PC_NAME_MAX')


async def noop_handler(request):
    return {"status": 218, "body": request["path"].encode()}


handler = apply_middleware(wrap_static(__test_data__, __here__))(noop_handler)
running_server = running_sever_fixture(build_server(handler))


@given(st.text(max_size=max_path_length))
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
        fs_path_length_ok = 0 < len(os.fsencode(path_name)) < max_path_length
        _, name_part = os.path.split(path_name)
        fs_name_length_ok = 0 < len(os.fsencode(name_part)) < max_filename_length
        
        quoted = quote(path_name, encoding=encoding)

        return fs_name_length_ok and fs_path_length_ok and not ("?" in path_name or "#" in path_name or "/" in path_name or "\x00" in path_name)
    except Exception:
        return False

def with_retry(func):
    for _ in range(3):
        result = func()
        if result.status_code == 200:
            return result
    return result 


@contextmanager
def delete_file_on_end(filename, keep):
    folder, _ = os.path.split(filename)
    if not os.path.exists(folder):
        os.makedirs(folder)
     
    try:
        yield
    except Exception:
        pass

    if folder == keep:
        os.unlink(filename)
        return
    
    try: 
        shutil.rmtree(folder)
    except Exception as error:
        print(error)
    
    


@given(url_path=st.text(max_size=max_path_length).filter(is_url_encodeable).filter(lambda s: s not in ["", "." ,".."]), content=st.binary(min_size=0, max_size=10*6))
@settings(max_examples=2000)
def test_all_urlencodeable_filenames_can_be_served_via_statics(running_server, url_path, content):
    base_dir, fname = os.path.split(url_path)
    local_static = os.path.join(__here__, __test_data__)
    
    test_file_full_path = os.path.join(local_static, base_dir, fname)

    debug_only_folder_name = os.path.join(local_static, base_dir)
    print("len static_folder: ", len(debug_only_folder_name), "Len Filename: ", len(fname), len(os.fsencode(debug_only_folder_name)) + len(os.fsencode(fname)), max_path_length)
    
    with delete_file_on_end(test_file_full_path, keep=local_static):
        with open(test_file_full_path, "wb") as tfile:
            tfile.write(content)
            tfile.flush()

            actual_fname = fname
            requested_path = running_server + actual_fname
            result = with_retry(lambda: requests.get(requested_path))
            response_url = unquote("/".join(result.url.split("/")[3:]))
            assert result.status_code == 200, f"File <{actual_fname.encode()}> not found, 'ServerPath': {result.content} {response_url}, {os.listdir(static_folder)}"
            assert result.content == content, f"File not found, {result}, {result.content}, {result.url}"


@given(url_path=st.text(max_size=max_path_length).filter(is_url_encodeable))
@settings(max_examples=2000)
def test_quote_unquote(url_path):
    assert os.fsencode(url_path) == os.fsencode(unquote(quote(url_path)))


@given(url_path=st.text(max_size=max_path_length).filter(is_url_encodeable).filter(lambda s: s not in ["", "." ,".."]))
@settings(max_examples=2000)
def test_files_can_be_arbitrary_encoded(url_path):
    with TemporaryDirectory() as td:
        print(url_path)
        with open(os.path.join(td, url_path), "w") as f:
            f.write("Peter Peter")
            f.flush()
            f.close()
        files = os.listdir(td)
        assert url_path in files


@given(url_path=st.text(max_size=max_path_length).filter(is_url_encodeable).filter(lambda x: x not in {".", ".."}))
@settings(max_examples=2000)
def test_requests_works_as_expected(running_server, url_path):
    response = requests.get(running_server + url_path)
    assert response.status_code == 218
    assert response.content == b"/" + unquote(url_path).encode()