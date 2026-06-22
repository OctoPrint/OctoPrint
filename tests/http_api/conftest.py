import os

import pytest

pytestmark = pytest.mark.http_api


@pytest.fixture
def baseURL():
    return os.environ.get("OCTOPRINT_BASEURL", "http://localhost:5000")


@pytest.fixture
def credentials():
    return {
        "username": os.environ.get("OCTOPRINT_USERNAME", "admin"),
        "password": os.environ.get("OCTOPRINT_PASSWORD", "test"),
        "apikey": os.environ.get(
            "OCTOPRINT_API_KEY", "yo5a103LN7co50R4_IAeLvGoLm08BpdfvKngzfHPcPE"
        ),
    }
