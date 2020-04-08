import os
import pytest
from multiprocessing import Process
from shallot import build_server
import uvicorn
import time
import string
from hypothesis import strategies as st


def running_sever_fixture(server_app):
    @pytest.fixture
    def running_server():
        server = server_app
        ip_port = ("127.0.0.1", 8550)
        process = Process(target=lambda: uvicorn.run(server, host=ip_port[0], port=ip_port[1], debug=True))
        process.start()
        time.sleep(1)
        yield f"http://{ip_port[0]}:{ip_port[1]}/"
        process.terminate()
        if process.is_alive():
            try:
                os.kill(process.pid)
            except:
                pass
        time.sleep(0.1)
    return running_server



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


# ------- rfc3986 definitions --------------

_unreserved = alpha + digits + "-._~"  # NOTE: differs from rfc1738
subdelims = "!$&'()*+,;="
st_pct_encoded = st.text(alphabet=string.hexdigits, min_size=2, max_size=2).map(lambda x: "%"+x)

st_pchar = st.text(alphabet=_unreserved) | st.text(alphabet=_unreserved) | st_pct_encoded | st.text(alphabet=":@")
st_query = st_pchar | st.text(alphabet="/?")
st_query_list =  st.lists(st_query, min_size=1)
# -------------------------------------------