import os

import pytest

pytestmark = pytest.mark.http_api


@pytest.fixture
def base_url():
    return os.environ.get("OCTOPRINT_BASEURL", "http://localhost:5000")


@pytest.fixture
def admin_credentials():
    return {
        "username": os.environ.get("OCTOPRINT_ADMIN_USERNAME", "admin"),
        "password": os.environ.get("OCTOPRINT_ADMIN_PASSWORD", "test"),
        "apikey": os.environ.get(
            "OCTOPRINT_ADMIN_API_KEY", "yo5a103LN7co50R4_IAeLvGoLm08BpdfvKngzfHPcPE"
        ),
    }


@pytest.fixture
def user_credentials():
    return {
        "username": os.environ.get("OCTOPRINT_USER_USERNAME", "user"),
        "password": os.environ.get("OCTOPRINT_USER_PASSWORD", "test"),
        "apikey": os.environ.get(
            "OCTOPRINT_USER_API_KEY", "paa1nMt86S3DTuLTJjeGQdI9CMNyCzZowIQzfJgPIso"
        ),
    }
