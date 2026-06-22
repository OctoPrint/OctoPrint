import http.client
from urllib.parse import urlencode, urlsplit

import pytest
import urllib3

pytestmark = pytest.mark.http_api

FILENAME = "usfhsec.gcode"
FOLDERNAME = "usfcsec"
PATH = "/path/to/secret.txt"
CONTENT = "M117 USFH Sec Test"
BOUNDARY = "RandomMultiPartBoundary1234567890"
CRLF = "\r\n"


def _percent_encode_fully(data):
    if not isinstance(data, bytes):
        data = data.encode()
    return "".join([f"%{c:02x}" for c in data])


BOUNDARY_ENCODED = _percent_encode_fully(BOUNDARY)
CRLF_ENCODED = _percent_encode_fully(CRLF)
SEMICOL_ENCODED = _percent_encode_fully(";")

##~~ regular requests working


@pytest.mark.parametrize(
    "body, content_type, path",
    [
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="file"; filename="{FILENAME}"{CRLF}'
                f"content-type: text/plain{CRLF}{CRLF}"
                f"{CONTENT}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            FILENAME,
            id="upload file",
        ),
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="file"; filename="{FILENAME}"{CRLF}'
                f"content-type: text/plain{CRLF}{CRLF}"
                f"{CONTENT}{CRLF}"
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="select"{CRLF}{CRLF}'
                f"true{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            FILENAME,
            id="upload file w/ select parameter",
        ),
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="foldername"{CRLF}{CRLF}'
                f"{FOLDERNAME}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            FOLDERNAME,
            id="create folder",
        ),
    ],
)
def test_regular_uploads_working(baseURL, headers, setup, body, content_type, path):
    hdrs = dict(**headers, **{"Content-Type": content_type})

    resp = urllib3.request("POST", baseURL + "/api/files/local", body=body, headers=hdrs)

    _verify_created(baseURL, headers, resp, path)


##~~ request parameters


@pytest.mark.parametrize("method", ["POST", "GET", "HEAD"])
def test_request_parameter_rejection(baseURL, headers, setup, method):
    query = urlencode({"file.name": FILENAME, "file.path": PATH})

    resp = urllib3.request(method, baseURL + "/api/files/local?" + query, headers=headers)

    _verify_rejected(baseURL, headers, resp)


##~~ application/x-www-form-urlencoded


def test_form_rejection(baseURL, headers, setup):
    body = urlencode({"file.name": FILENAME, "file.path": PATH})
    hdrs = dict(**headers, **{"Content-Type": "aPplicaTion/X-wWW-FOrm-uRLenCodEd"})

    resp = urllib3.request(
        "POST",
        baseURL + "/api/files/local",
        headers=hdrs,
        body=body,
    )

    _verify_rejected(baseURL, headers, resp)


##~~ multipart/form-data


@pytest.mark.parametrize(
    "body, content_type",
    [
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="file.name"{CRLF}{CRLF}'
                f"{FILENAME}{CRLF}"
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="file.path"{CRLF}{CRLF}'
                f"{PATH}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            id="basic injection",
        ),
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="file.name"{CRLF}{CRLF}'
                f"{FILENAME}{CRLF}"
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="file.path"{CRLF}{CRLF}'
                f"{PATH}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"mUltIpaRt/FORM-dAta; boundary={BOUNDARY}",
            id="randomly cased content type",
        ),
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'Content-Disposition: form-data; name="file"; filename*=utf-8\'\'{FILENAME}{CRLF_ENCODED}--{BOUNDARY_ENCODED}{CRLF_ENCODED}Content-Disposition: form-data{SEMICOL_ENCODED} name="file.path"{CRLF_ENCODED}{CRLF_ENCODED}{PATH}{CRLF}'
                f"Content-Type: application/octet-stream{CRLF}{CRLF}"
                f"{CONTENT}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            id="body injection in RFC 5987 filename",
        ),
    ],
)
def test_multipart_rejection(baseURL, headers, setup, body, content_type):
    hdrs = dict(**headers, **{"Content-Type": content_type})

    resp = urllib3.request("POST", baseURL + "/api/files/local", body=body, headers=hdrs)

    _verify_rejected(baseURL, headers, resp)


def test_multipart_obs_fold_rejection(baseURL, headers, setup):
    # we do this via a socket to make sure nothing transparently removes the obs fold
    import socket

    url = urlsplit(baseURL)

    body = (
        f"--{BOUNDARY}{CRLF}"
        f'content-disposition: form-data; name="file.name"{CRLF}{CRLF}'
        f"{FILENAME}{CRLF}"
        f"--{BOUNDARY}{CRLF}"
        f'content-disposition: form-data; name="file.path"{CRLF}{CRLF}'
        f"{PATH}{CRLF}"
        f"--{BOUNDARY}--{CRLF}"
    )
    hdrs = dict(
        **headers, **{"Content-Type": f"{CRLF} multipart/form-data; boundary=" + BOUNDARY}
    )

    req = (
        f"POST /api/files/local HTTP/1.1{CRLF}"
        + f"Host: {url.netloc}{CRLF}"
        + f"Content-Length: {len(body)}{CRLF}"
        + f"{CRLF}".join(f"{k}: {v}" for k, v in hdrs.items())
        + f"{CRLF}{CRLF}"
        + body
    )

    # send request
    s = socket.create_connection((url.hostname, url.port))
    s.sendall(req.encode())

    # parse response
    resp = http.client.HTTPResponse(s, method="POST")
    resp.begin()

    # verify
    _verify_rejected(baseURL, headers, resp)


@pytest.mark.parametrize(
    "body, content_type",
    [
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="x\\"; name=\\"file.name\\"; z=\\"y"{CRLF}{CRLF}'
                f"{FILENAME}{CRLF}"
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="x\\"; name=\\"file.path\\"; z=\\"y"{CRLF}{CRLF}'
                f"{PATH}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            id="quote escape in quoted field",
        ),
        pytest.param(
            (
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name=x\\"; name=\\"file.name\\"; z=\\"y{CRLF}{CRLF}'
                f"{FILENAME}{CRLF}"
                f"--{BOUNDARY}{CRLF}"
                f'content-disposition: form-data; name="x\\"; name=\\"file.path\\"; z=\\"y"{CRLF}{CRLF}'
                f"{PATH}{CRLF}"
                f"--{BOUNDARY}--{CRLF}"
            ),
            f"multipart/form-data; boundary={BOUNDARY}",
            id="quote escape in unquoted field",
        ),
    ],
)
def test_multipart_noop(baseURL, headers, setup, body, content_type):
    hdrs = dict(**headers, **{"Content-Type": content_type})

    resp = urllib3.request("POST", baseURL + "/api/files/local", body=body, headers=hdrs)

    _verify_noop(baseURL, headers, resp)


##~~ helpers


def _ensure_path_unknown(baseURL, headers, path):
    resp = urllib3.request("DELETE", f"{baseURL}/api/files/local/{path}", headers=headers)
    if resp.status not in [204, 404]:
        pytest.fail(
            f"unexpected status returned on path unknown check for `{path}`: {resp.status}"
        )


##~~ verifiers


def _verify_created(baseURL, headers, resp, path):
    assert resp.status == 201

    resp = urllib3.request(
        "GET",
        f"{baseURL}/api/files/local/{path}",
        headers=headers,
    )
    assert resp.status == 200


def _verify_rejected(baseURL, headers, resp):
    # should be Bad Request
    assert resp.status == 400

    # content type text/html indicates error generated inside the custom upload handler vs Flask,
    # so that's what we check here
    assert "text/html" in resp.headers.get("content-type")

    # also make sure no file got uploaded
    _verify_path_missing(baseURL, headers, FILENAME)


def _verify_noop(baseURL, headers, resp):
    # should be Bad Request
    assert resp.status == 400

    # content type application/json indicates error generated by Flask,
    # so that's what we check here
    assert "application/json" in resp.headers.get("content-type")

    # check that Flask complains about missing upload data
    body = resp.json()
    assert body.get("error") == "No file to upload and no folder to create"

    # also make sure no file got uploaded
    _verify_path_missing(baseURL, headers, FILENAME)


def _verify_path_missing(baseURL, headers, path):
    resp = urllib3.request(
        "GET",
        f"{baseURL}/api/files/local/{path}",
        headers=headers,
    )
    assert resp.status == 404


##~~ fixtures


@pytest.fixture
def headers(credentials):
    return {"Authorization": f"Bearer {credentials['apikey']}"}


@pytest.fixture
def setup(baseURL, headers, caplog):
    _ensure_path_unknown(baseURL, headers, FILENAME)
    _ensure_path_unknown(baseURL, headers, FILENAME)
