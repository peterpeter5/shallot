from collections import defaultdict
from aring.response import filestream


def unicode2(xys, encoding="utf-8"):
    x, y = xys
    return (x.decode(encoding), y.decode(encoding)) 

def lowercase_key(xys):
    x, y = xys
    return (x.lower(), y) 


def make_headers_map(headers):
    """
    all header-fields are joined here! This is against:  RFC 7230 and RFC 6265 (Coockies)
    However: the final request will provide the original-headers-list. So this convinient is ok! 
    """
    acc = defaultdict(list)
    for key, value in map(lambda xy: lowercase_key(unicode2(xy)), headers):
        acc[key].append(value)

    return {
        k: ",".join(v) for k, v in acc.items()
    }



async def consume_body(receive):
        body = b''
        more_body = True

        while more_body:
            message = await receive()
            body += message.get('body', b'')
            more_body = message.get('more_body', False)

        return body
 

async def responde_client(send, response):
    streaming = response.get("stream")
    if not streaming:
        await _responde_client_direct(send, response)
    else:
        await _responde_client_chunked(send, response)
    
async def _responde_client_chunked(send, response):
    status = response['status']
    headers = [(k.encode("utf-8"), v.encode("utf-8")) for k,v in response.get("headers", {}).items()]
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers
    })
    bytestream = response['stream']
    async for chunk in bytestream:
        await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
    await send({'type': 'http.response.body', 'body': b'', 'more_body': False})
        


async def _responde_client_direct(send, response):
    status = response['status']
    headers = [(k.encode("utf-8"), v.encode("utf-8")) for k,v in response.get("headers", {}).items()]
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers
    })
    await send({
        'type': 'http.response.body',
        'body': response.get("body", b''),
    })


def build_server(handler):
    def request_start(context):
        async def handle_handler(receive, send):
            headers_list = context.get('headers', [])
            headers = make_headers_map(headers_list)
            body = await consume_body(receive)
            server_name, server_port = context.get('server', (None, None))
            request = {
                **context, 
                "headers": headers, 'body': body, 'headers_list': headers_list,
                "server_name": server_name, "server_port": server_port
            }

            response = await handler(request)
            # TOOO validate response!
            await responde_client(send, response)
            return response

        return handle_handler
    return request_start


async def hello_world(request):
    msg = "Hello World  -> handler 1 \n\n\n %s" % request
    msg = msg.encode()
    return {"status": 200, "body": msg}
    

if __name__ == "__main__":
    import uvicorn
    from aring.middlewares.staticfiles import wrap_static
    from aring.middlewares.cors import wrap_cors
    from aring.middlewares.content_type import wrap_content_type
    content_types = wrap_content_type()
    statics = wrap_static("/home/peter/PycharmProjects/a-ring/test/data")
    cors = wrap_cors()
    server = build_server(content_types(cors(statics(hello_world))))
    uvicorn.run(server, "127.0.0.1", 5000, log_level="info", debug=True)

        