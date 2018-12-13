import os
import re
from urllib.parse import unquote
from aring.response import responde404, filestream, responde_not_modified
from aiofiles.os import stat as astat
from email.utils import formatdate
from hashlib import md5
import stat


def validate_dir_path(path):
    return path and os.path.isdir(path) 


def file_exists(path):
    return path and os.path.isfile(path)


def make_caching_headers(filestats):
    etag_base = str(filestats.st_mtime) + "-" + str(filestats.st_size)
    etag = md5(etag_base.encode()).hexdigest()
    return {
        "last-modified" : formatdate(filestats.st_mtime, usegmt=True),
        "content-length": str(filestats.st_size),
        "etag":  etag
    }


def extract_matching_cache(client_headers):
    last_modified = client_headers.get("if-modified-since")
    etag = client_headers.get("if-none-match")
    return {
        k: v
        for k, v in [("last-modified", last_modified), ("etag", etag)]
        if v is not None
    }


def wrap_static(static_folder, root_path=".", allow_symlinks=False):
    static_folder = os.path.split(static_folder)
    root_to_check_against = os.path.abspath(os.path.join(root_path, *static_folder))
    
    if not validate_dir_path(root_to_check_against):
        raise NotADirectoryError(f"the provided path <{root_to_check_against}> is not a directory!")
    
    def wrap_static_files(handler):
        async def _handle_request(request):
            if request['method'] not in {"GET", "HEAD"}:
                return await handler(request)
            
            raw_path = request['path']
            if "../" in raw_path:
                return responde404()
            
            requested_path = os.path.abspath(unquote(os.path.join(
                root_path, *static_folder, re.sub("^[/]*", "", raw_path)))
            ) 
            if not (requested_path.startswith(root_to_check_against) and file_exists(requested_path)):
                return await handler(request)

            fstat = await astat(requested_path)
            if stat.S_ISLNK(fstat.st_mode) and not allow_symlinks:
                return responde404()
            
            caching_headers = make_caching_headers(fstat)
            client_caching_headers = extract_matching_cache(request.get("headers", {}))
            if client_caching_headers and client_caching_headers.items() <= caching_headers.items():
                return responde_not_modified(caching_headers)
            else:
                return filestream(requested_path, headers=caching_headers)

        return _handle_request
    return wrap_static_files

