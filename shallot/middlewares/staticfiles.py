import os
import re
from shallot.response import respond404, filestream, respond_not_modified
from aiofiles.os import stat as astat
from email.utils import formatdate
from hashlib import md5


def validate_dir_path(path):
    return path and os.path.isdir(path)


def file_exists(path):
    return path and "\x00" not in path and os.path.isfile(path)


def make_caching_headers(filestats):
    etag_base = str(filestats.st_mtime) + "-" + str(filestats.st_size)
    etag = md5(etag_base.encode()).hexdigest()
    return {
        "last-modified": formatdate(filestats.st_mtime, usegmt=True),
        "content-length": str(filestats.st_size),
        "etag": etag,
    }


def extract_matching_cache(client_headers):
    last_modified = client_headers.get("if-modified-since")
    etag = client_headers.get("if-none-match")
    return {k: v for k, v in [("last-modified", last_modified), ("etag", etag)] if v is not None}


def wrap_static(static_folder, root_path="."):
    static_folder = os.path.split(static_folder)
    root_to_check_against = os.path.abspath(os.path.join(root_path, *static_folder))

    if not validate_dir_path(root_to_check_against):
        raise NotADirectoryError(f"the provided path <{root_to_check_against}> is not a directory!")

    def wrap_static_files(next_middleware):
        async def _handle_request(handler, request):
            if request["method"] not in {"GET", "HEAD"}:
                return await next_middleware(handler, request)

            raw_path = request["path"]
            if "../" in raw_path:
                return respond404()

            requested_path = os.path.abspath(os.path.join(root_path, *static_folder, re.sub("^[/]*", "", raw_path)))
            if not (requested_path.startswith(root_to_check_against) and file_exists(requested_path)):
                return await next_middleware(handler, request)

            fstat = await astat(requested_path)

            caching_headers = make_caching_headers(fstat)
            client_caching_headers = extract_matching_cache(request.get("headers", {}))

            if client_caching_headers and client_caching_headers.items() <= caching_headers.items():
                return respond_not_modified(caching_headers)
            else:
                return filestream(requested_path, headers=caching_headers)

        return _handle_request

    return wrap_static_files
