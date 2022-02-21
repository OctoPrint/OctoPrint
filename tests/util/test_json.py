__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

import datetime
import time
import warnings

import pytest
from frozendict import frozendict

from octoprint.util import json


class SomeClass:
    ...


class SomeSubclass(frozendict):
    ...


def test_deprecated_dump():
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as w:
        assert json.dump({"foo": "bar"}) == '{"foo":"bar"}'

        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert "dump has been renamed to dumps" in str(w[-1].message)


@pytest.mark.parametrize(
    "val,expected",
    [
        pytest.param({"foo": "bar"}, '{"foo":"bar"}', id="dict"),
        pytest.param(frozendict({"foo": "bar"}), '{"foo":"bar"}', id="frozendict"),
        pytest.param(b"foo", '"foo"', id="bytes"),
    ],
)
def test_encoding_dumps(val, expected):
    assert json.encoding.dumps(val) == expected


def test_encoding_loads():
    assert json.encoding.loads('{"foo":"bar"}') == {"foo": "bar"}


def test_encoding_dumps_typeerror():
    with pytest.raises(TypeError):
        json.encoding.dumps(SomeClass())


@pytest.mark.parametrize(
    "val",
    [
        pytest.param({"foo": "bar"}, id="dict"),
        pytest.param(b"\x00\x01\x02\x03", id="bytes"),
        pytest.param(frozendict({"foo": "bar"}), id="frozendict"),
        pytest.param(time.struct_time((2018, 1, 1, 0, 0, 0, 0, 0, 0)), id="struct_time"),
        pytest.param(
            datetime.datetime(2022, 3, 21, 5, 24, 0, 0, tzinfo=datetime.timezone.utc),
            id="datetime",
        ),
        pytest.param(frozendict({"a": b"b"}), id="nested"),
        pytest.param(SomeSubclass({"a": b"b"}), id="subclass"),
    ],
)
def test_serializing_roundtrips(val):
    assert json.serializing.loads(json.serializing.dumps(val)) == val


def test_serializing_dumps_typeerror():
    with pytest.raises(TypeError):
        json.serializing.dumps(SomeClass())
