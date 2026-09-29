import pytest
from click.testing import CliRunner

import octoprint.settings
from octoprint.cli import octo


@pytest.fixture
def basedir(tmp_path, monkeypatch):
    # reset settings manager instance for each test
    monkeypatch.setattr(octoprint.settings, "_instance", None)
    return str(tmp_path / "basedir")


@pytest.fixture
def overlay(tmp_path):
    path = tmp_path / "overlay.yaml"
    path.write_text("server:\n  host: 1.2.3.4\n")
    return str(path)


@pytest.mark.parametrize(
    "args",
    [
        ["get", "server.host"],
        ["set", "server.host", "1.2.3.4"],
        ["remove", "server.host"],
        ["append_value", "foo.bar", "baz"],
        ["insert_value", "foo.bar", "0", "baz"],
        ["remove_value", "foo.bar", "baz"],
    ],
)
def test_config_commands(basedir, args):
    result = CliRunner().invoke(octo, ["-b", basedir, "config", *args])

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "command",
    [
        "--overlay {overlay} config get server.host",
        "config --overlay {overlay} get server.host",
        "config get --overlay {overlay} server.host",
        "config get server.host --overlay {overlay}",
    ],
)
def test_config_overlay_position(basedir, overlay, command):
    args = command.format(overlay=overlay).split()
    result = CliRunner().invoke(octo, ["-b", basedir, *args])

    assert result.exit_code == 0
    assert result.output.strip() == "'1.2.3.4'"
