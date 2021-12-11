__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import time

from frozendict import frozendict

from octoprint.util import comprehensive_json


def test_bytes_roundtrip():
    val = b"\x00\x01\x02\x03"
    res = comprehensive_json.dumps(val)
    assert res == '"\\u0000\\u0001\\u0002\\u0003"'
    assert comprehensive_json.loads(res) == "\x00\x01\x02\x03"


def test_frozendict_roundtrip():
    val = frozendict({"a": "b"})
    res = comprehensive_json.dumps(val)
    assert res == '{"a":"b"}'
    assert comprehensive_json.loads(res) == dict(val)


def test_nested_custom_types():
    val = frozendict({"a": b"b"})
    res = comprehensive_json.dumps(val)
    assert res == '{"a":"b"}'
    assert comprehensive_json.loads(res) == {"a": "b"}


def test_struct_time():
    # we want to make sure we don't treat all tuples as struct_time
    assert comprehensive_json.dumps((1, 2, 3)) == "[1,2,3]"

    val = time.struct_time((2018, 1, 1, 0, 0, 0, 0, 0, 0))
    res = comprehensive_json.dumps(val)
    assert res == '{"__jsonclass__":["struct_time",[2018,1,1,0,0,0,0,0,0]]}'
    assert comprehensive_json.loads(res) == val


def test_subclass_encode():
    class MyClass(frozendict):
        ...

    assert comprehensive_json.dumps(MyClass({"a": "b"})) == '{"a":"b"}'
