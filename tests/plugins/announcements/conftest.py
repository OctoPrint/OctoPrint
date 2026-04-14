from unittest import mock

import pytest

from octoprint.plugins.announcements import AnnouncementPlugin


@pytest.fixture(scope="module")
def plugin():
    instance = AnnouncementPlugin()
    instance._logger = mock.MagicMock()

    yield instance
