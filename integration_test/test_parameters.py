import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from .helper import st_query_list, running_sever_fixture
from shallot.response import json
from shallot.middlewares import wrap_parameters, apply_middleware
import requests
from itertools import zip_longest
from shallot import build_server


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


async def handle_any_request(request):
    return json({
        "query_string": request["query_string"].decode(),
        "params": request["params"],
        "query_params": request["query_params"],
        "form_params": request["form_params"],
    })


handler = apply_middleware(wrap_parameters(keep_blank_values=True))(handle_any_request)
running_server = running_sever_fixture(build_server(handler))


@given(st.text())
@settings(max_examples=1000)
def test_arbitrary_query_strings_dont_return_500(running_server, qstring):
    url = running_server + "a?" + qstring
    response = requests.get(url)
    assert response.status_code == 200, f"Error for url {url}, reponse: {response.content}"


@given(st_query_list)
@settings(max_examples=1000)
def test_all_qstrings_can_be_grouped_and_joined_for_forms_and_standard_queries_url(running_server, queries):
    expected_params = dict(grouper(queries, 2, "-0"))
    response = requests.get(running_server, params=expected_params)
    assert response.status_code == 200, f"Error for url {response.url}, reponse: {response.content}"
    assert response.json()["params"] == {k: [v] for k, v in expected_params.items()}


@given(st_query_list) 
@settings(max_examples=1000)
def test_all_url_encoded_bodies_work_same_as_url_qstrings(running_server, queries):
    expected_params = dict(grouper(queries, 2, "-0"))
    response = requests.post(running_server, data=expected_params)
    assert response.status_code == 200, f"Error for url {response.url}, reponse: {response.content}"
    assert response.json()["params"] == {k: [v] for k, v in expected_params.items()}


@given(url_q=st_query_list, form_q=st_query_list) 
@settings(max_examples=1000)
def test_body_and_url_params_can_be_mixed(running_server, url_q, form_q):
    expected_url_params = dict(grouper(url_q, 2, "-0"))
    expected_form_params = dict(grouper(form_q, 2, "+0"))
    
    response = requests.post(running_server, data=expected_form_params, params=expected_url_params)
    assert response.status_code == 200, f"Error for url {response.url}, reponse: {response.content}"
    expected_reslut = {}
    expected_reslut.update(expected_url_params)
    expected_reslut.update(expected_form_params)
    assert response.json()["params"] == {k: [v] for k, v in expected_reslut.items()}
    assert response.json()["form_params"] == {k: [v] for k, v in expected_form_params.items()}
    assert response.json()["query_params"] == {k: [v] for k, v in expected_url_params.items()}
