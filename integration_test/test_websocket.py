from .helper import running_sever_fixture
from shallot import websocket, build_server
import asyncio 
import websockets
import pytest
import os
import sys
import time
here = os.path.dirname(__file__)
tutorials_path = os.path.join(here, "..", "tutorial")
sys.path.append(tutorials_path)

from tutorial_04 import app as _simple_ws_app


@websocket
async def never_collect_messages(scope, receiver):
    while True: 
        await asyncio.sleep(1)


ws_never_collect = running_sever_fixture(build_server(never_collect_messages))
ws_simple = running_sever_fixture(_simple_ws_app)


@pytest.mark.asyncio
@pytest.mark.skip
async def test_never_collect_messages(ws_never_collect):
    index = 0
    bytes_send = 0.0
    async with websockets.connect(ws_never_collect.replace("http", "ws")) as ws:
        
        while True:
            index += 1
            data = "testdata"*128*int(1024)
            bytes_send += len(data) / (1024)
            try:
                await ws.send(data)
            except:
                break

            if index % 100 == 0:
                print(f"send {bytes_send / (1024)} MB")
    assert bytes_send / (1024) > 8.0  


@pytest.mark.asyncio
async def test_tutorial_fan_in(ws_simple):
    fan_in = ws_simple.replace("http", "ws") + "fan-in"
    async with websockets.connect(fan_in) as ws:
        await ws.send("mbl: This is just a message!")

    assert True, "I was able to send a message to fan-in"


@pytest.mark.asyncio
async def test_tutorial_fan_out(ws_simple):
    fan_out = ws_simple.replace("http", "ws") + "fan-out"
    async with websockets.connect(fan_out) as ws:
        message = await ws.recv()
        assert "time" in message.lower()
        start = time.time()
        second_message = await ws.recv()
        assert "time" in second_message.lower()
        end = time.time()
        
    assert 1 < (end - start) < 2, "The timing between the messages was not correct"


@pytest.mark.asyncio
async def test_tutorial_chatbot(ws_simple):
    chat = ws_simple.replace("http", "ws") + "chatbot"
    async with websockets.connect(chat) as ws:
        await ws.send("hello")
        message = await ws.recv()
        assert "hello beautiful" in message.lower()

        await ws.send("i like you")
        message = await ws.recv()
        assert "that is very nice" in message.lower()

        await ws.send("mbl: this text is unknown")
        message = await ws.recv()
        assert "pardon me" in message.lower()
