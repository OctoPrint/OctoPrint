__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

from ddt import data, ddt, unpack


@ddt
class TestCommHelpers(unittest.TestCase):
    @data(
        ("M117 Test", "M117 Test"),
        ("M117 Test ; foo", "M117 Test "),
        ("M117 Test \\; foo", "M117 Test \\; foo"),
        ("M117 Test \\\\; foo", "M117 Test \\\\"),
        ("M117 Test \\\\\\; foo", "M117 Test \\\\\\; foo"),
        ("; foo", ""),
    )
    @unpack
    def test_strip_comment(self, input, expected):
        from octoprint.util import comm

        self.assertEqual(expected, comm.strip_comment(input))

    @data(
        ("M117 Test", None, None, "M117 Test"),
        ("", None, None, None),
        ("  \t \r    \n", None, None, None),
        ("M117 Test", {}, 0, "M117 Test"),
    )
    @unpack
    def test_process_gcode_line(self, input, offsets, current_tool, expected):
        from octoprint.util import comm

        self.assertEqual(
            expected,
            comm.process_gcode_line(input, offsets=offsets, current_tool=current_tool),
        )

    @data(
        ("M104 S200", None, None, None),
        ("M117 Test", {}, None, None),
        ("M104 T0", {}, None, None),
        ("M104 S220", {"tool0": 10, "tool1": 20, "bed": 30}, 0, 230.0),
        ("M104 T1 S220", {"tool0": 10, "tool1": 20, "bed": 30}, 0, 240.0),
        ("M104 S220", {"tool0": 10, "tool1": 20, "bed": 30}, 1, 240.0),
        ("M140 S100", {"tool0": 10, "tool1": 20, "bed": 30}, 1, 130.0),
        ("M190 S100", {"tool0": 10, "tool1": 20, "bed": 30}, 1, 130.0),
        ("M109 S220", {"tool0": 10, "tool1": 20, "bed": 30}, 0, 230.0),
        ("M109 S220", {}, 0, None),
        ("M140 S100", {}, 0, None),
        ("M104 S220", {"tool0": 0}, 0, None),
        ("M104 S220", {"tool0": 20}, None, None),
        ("M104 S0", {"tool0": 20}, 0, None),
    )
    @unpack
    def test_apply_temperature_offsets(self, input, offsets, current_tool, expected):
        from octoprint.util import comm

        actual = comm.apply_temperature_offsets(input, offsets, current_tool=current_tool)

        if expected is None:
            self.assertEqual(input, actual)
        else:
            import re

            match = re.search(r"S(\d+(\.\d+)?)", actual)
            if not match:
                self.fail("No temperature found")
            temperature = float(match.group(1))
            self.assertEqual(expected, temperature)
            self.assertEqual(input[: match.start(1)], actual[: match.start(1)])
            self.assertEqual(input[match.end(1) :], actual[match.end(1) :])

    def test_convert_pause_triggers(self):
        configured_triggers = [
            {"regex": "pause1", "type": "enable"},
            {"regex": "pause2", "type": "enable"},
            {"regex": "resume", "type": "disable"},
            {"regex": "toggle", "type": "toggle"},
            {"type": "enable"},
            {"regex": "regex"},
            {"regex": "regex", "type": "unknown"},
        ]

        from octoprint.util import comm

        trigger_matchers = comm.convert_pause_triggers(configured_triggers)

        self.assertIsNotNone(trigger_matchers)

        self.assertIn("enable", trigger_matchers)
        self.assertEqual("(pause1)|(pause2)", trigger_matchers["enable"].pattern)

        self.assertIn("disable", trigger_matchers)
        self.assertEqual("(resume)", trigger_matchers["disable"].pattern)

        self.assertIn("toggle", trigger_matchers)
        self.assertEqual("(toggle)", trigger_matchers["toggle"].pattern)

        self.assertNotIn("unknown", trigger_matchers)

    def test_convert_feedback_controls(self):
        def md5sum(input):
            import hashlib

            m = hashlib.md5()
            m.update(input)
            return m.hexdigest()

        # rb'' doesn't exist in Python2
        temp_regex = rb"T:((\d*\.)\d+)"
        temp_template = b"Temp: {}"
        temp2_template = b"Temperature: {}"
        temp_key = md5sum(temp_regex)
        temp_template_key = md5sum(temp_template)
        temp2_template_key = md5sum(temp2_template)

        x_regex = rb"X:(?P<x>\d+)"
        x_template = b"X: {x}"
        x_key = md5sum(x_regex)
        x_template_key = md5sum(x_template)

        configured_controls = [
            {
                "key": temp_key,
                "regex": temp_regex,
                "template": temp_template,
                "template_key": temp_template_key,
            },
            {"command": "M117 Hello World", "name": "Test"},
            {
                "children": [
                    {
                        "key": x_key,
                        "regex": x_regex,
                        "template": x_template,
                        "template_key": x_template_key,
                    },
                    {
                        "key": temp_key,
                        "regex": temp_regex,
                        "template": temp2_template,
                        "template_key": temp2_template_key,
                    },
                ]
            },
        ]

        from octoprint.util import comm

        controls, matcher = comm.convert_feedback_controls(configured_controls)

        self.assertEqual(2, len(controls))

        # temp_regex is used twice, so we should have two templates for it
        self.assertIn(temp_key, controls)
        temp = controls[temp_key]

        self.assertIsNotNone(temp["matcher"])
        self.assertEqual(temp_regex, temp["matcher"].pattern)
        self.assertEqual(temp_regex, temp["pattern"])

        self.assertEqual(2, len(temp["templates"]))
        self.assertIn(temp_template_key, temp["templates"])
        self.assertEqual(temp_template, temp["templates"][temp_template_key])
        self.assertIn(temp2_template_key, temp["templates"])
        self.assertEqual(temp2_template, temp["templates"][temp2_template_key])

        # x_regex is used once, so we should have only one template for it
        self.assertIn(x_key, controls)
        x = controls[x_key]

        self.assertIsNotNone(x["matcher"])
        self.assertEqual(x_regex, x["matcher"].pattern)
        self.assertEqual(x_regex, x["pattern"])

        self.assertEqual(1, len(x["templates"]))
        self.assertIn(x_template_key, x["templates"])
        self.assertEqual(x_template, x["templates"][x_template_key])

        self.assertEqual(
            f"(?P<group{temp_key}>{temp_regex})|(?P<group{x_key}>{x_regex})",
            matcher.pattern,
        )

    @data(
        ("G4 P2.0", "floatP", True, "2.0"),
        ("M109 S220.0", "floatS", True, "220.0"),
        ("G1 X10.0 Y10.0 Z0.2", "floatZ", True, "0.2"),
        ("G1X10.0Y10.0Z0.2", "floatZ", True, "0.2"),
        ("g1x10.0y10.0z0.2", "floatZ", True, "0.2"),
        ("M110 N0", "intN", True, "0"),
        ("M104 S220.0 T1", "intT", True, "1"),
        ("M104 T1 S220.0", "intT", True, "1"),
        ("N100 M110", "intN", True, "100"),
        ("NP100", "floatP", False, None),
    )
    @unpack
    def test_parameter_regexes(self, line, parameter, should_match, expected_value):
        from octoprint.util.comm import regexes_parameters

        regex = regexes_parameters[parameter]
        match = regex.search(line)

        if should_match:
            self.assertIsNotNone(match)
            self.assertEqual(expected_value, match.group("value"))
        else:
            self.assertIsNone(match)

    @data(
        ("G0 X0", "G0"),
        ("G28 X0 Y0", "G28"),
        ("M109 S220.0 T1", "M109"),
        ("M117 Hello World", "M117"),
        ("T0", "T"),
        ("T3", "T"),
        (None, None),
        ("No match", None),
    )
    @unpack
    def test_gcode_command_for_cmd(self, cmd, expected):
        from octoprint.util.comm import gcode_command_for_cmd

        result = gcode_command_for_cmd(cmd)
        self.assertEqual(expected, result)

    @data(
        ("G0 X0", "G0", None),
        ("M105", "M105", None),
        ("T2", "T", None),
        ("M80.1", "M80", "1"),
        ("G28.2", "G28", "2"),
        ("T0.3", "T", None),
        ("M80.nosubcode", "M80", None),
        (None, None, None),
        ("No match", None, None),
    )
    @unpack
    def test_gcode_and_subcode_for_cmd(self, cmd, expected_gcode, expected_subcode):
        from octoprint.util.comm import gcode_and_subcode_for_cmd

        actual_gcode, actual_subcode = gcode_and_subcode_for_cmd(cmd)
        self.assertEqual(expected_gcode, actual_gcode)
        self.assertEqual(expected_subcode, actual_subcode)

    @data(
        ("T:23.0 B:60.0", 0, {"T0": (23.0, None), "B": (60.0, None)}, 0),
        ("T:23.0 B:60.0", 1, {"T1": (23.0, None), "B": (60.0, None)}, 1),
        ("T:23.0/220.0 B:60.0/70.0", 0, {"T0": (23.0, 220.0), "B": (60.0, 70.0)}, 0),
        (
            "ok T:23.0/220.0 T0:23.0/220.0 T1:50.2/210.0 T2:39.4/220.0 B:60.0",
            0,
            {
                "T0": (23.0, 220.0),
                "T1": (50.2, 210.0),
                "T2": (39.4, 220.0),
                "B": (60.0, None),
            },
            2,
        ),
        (
            "ok T:50.2/210.0 T0:23.0/220.0 T1:50.2/210.0 T2:39.4/220.0 B:60.0",
            1,
            {
                "T0": (23.0, 220.0),
                "T1": (50.2, 210.0),
                "T2": (39.4, 220.0),
                "B": (60.0, None),
            },
            2,
        ),
        (
            "ok T:-55.7/0 T0:-55.7/0 T1:150.0/210.0",
            0,
            {"T0": (-55.7, 0), "T1": (150.0, 210.0)},
            1,
        ),
        (
            "ok T:150.0/210.0 T0:-55.7/0 T1:150.0/210.0",
            1,
            {"T0": (-55.7, 0), "T1": (150.0, 210.0)},
            1,
        ),
        (
            "T:210.04 /210.00 B:52.00 /52.00 @:85 B@:31pS_XYZ:5",
            0,
            {
                "T0": (210.04, 210.0),
                "B": (52.00, 52.0),
            },
            0,
        ),
        (
            "T:210.04 /210.00 B:52.00 /52.00 @:85 31pS_XYZ:5",
            0,
            {
                "T0": (210.04, 210.0),
                "B": (52.00, 52.0),
                "31pS_XYZ": (5, None),
            },
            0,
        ),
        (
            "T:210.04 /210.00 B:52.00 /52.00 @:85 F0:255.0 /255.0",
            0,
            {
                "T0": (210.04, 210.0),
                "B": (52.00, 52.0),
                "F0": (255.0, 255.0),
            },
            0,
        ),
        (
            "T:210.04 /210.00 @B:52.00 /52.00",
            0,
            {
                "T0": (210.04, 210.0),
            },
            0,
        ),
        (
            "T:210.04 /210.00 @B:52.00 /52.00 TXYZ:2",
            0,
            {
                "T0": (210.04, 210.0),
                "TXYZ": (2, None),
            },
            0,
        ),
        (
            # Only first occurrence of a sensor should be used, second B gets ignored
            "T:210.04 /210.00 B:52.00 /52.00 @:85 B:1234.0 /1234.0",
            0,
            {
                "T0": (210.04, 210.0),
                "B": (52.00, 52.0),
            },
            0,
        ),
    )
    @unpack
    def test_process_temperature_line(self, line, current, expected_result, expected_max):
        from octoprint.util.comm import parse_temperature_line

        maxtool, result = parse_temperature_line(line, current)
        self.assertDictEqual(expected_result, result)
        self.assertEqual(expected_max, maxtool)

    @data(
        # T => T0
        ({"T": (23.0, None)}, 0, {"T0": (23.0, None)}),
        # T => T1
        ({"T": (23.0, None)}, 1, {"T1": (23.0, None)}),
        # T and Tn present => Tn wins
        (
            {"T": (23.0, None), "T0": (23.0, None), "T1": (42.0, None)},
            0,
            {"T0": (23.0, None), "T1": (42.0, None)},
        ),
        (
            {"T": (42.0, None), "T0": (23.0, None), "T1": (42.0, None)},
            1,
            {"T0": (23.0, None), "T1": (42.0, None)},
        ),
        (
            {"T": (21.0, None), "T0": (23.0, None), "T1": (42.0, None)},
            0,
            {"T0": (23.0, None), "T1": (42.0, None)},
        ),
        (
            {"T": (41.0, None), "T0": (23.0, None), "T1": (42.0, None)},
            1,
            {"T0": (23.0, None), "T1": (42.0, None)},
        ),
        # T and no T0 => Smoothieware, T = T0
        (
            {"T": (23.0, None), "T1": (42.0, None)},
            1,
            {"T0": (23.0, None), "T1": (42.0, None)},
        ),
        # no T => as-is
        (
            {"T0": (23.0, None), "T1": (42.0, None)},
            1,
            {"T0": (23.0, None), "T1": (42.0, None)},
        ),
    )
    @unpack
    def test_canonicalize_temperatures(self, parsed, current, expected):
        from octoprint.util.comm import canonicalize_temperatures

        result = canonicalize_temperatures(parsed, current)
        self.assertDictEqual(expected, result)

    @data(
        (
            "KEY1:Value 1 FIRMWARE_NAME:Some Firmware With Spaces KEY2:Value 2",
            {
                "KEY1": "Value 1",
                "KEY2": "Value 2",
                "FIRMWARE_NAME": "Some Firmware With Spaces",
            },
        ),
        (
            "NAME: Malyan VER: 2.9 MODEL: M200 HW: HA02",
            {"NAME": "Malyan", "VER": "2.9", "MODEL": "M200", "HW": "HA02"},
        ),
        (
            "NAME. Malyan	VER: 3.8	MODEL: M100	HW: HB02",
            {"NAME": "Malyan", "VER": "3.8", "MODEL": "M100", "HW": "HB02"},
        ),
        (
            "NAME. Malyan VER: 3.7 MODEL: M300 HW: HG01",
            {"NAME": "Malyan", "VER": "3.7", "MODEL": "M300", "HW": "HG01"},
        ),
        (
            "FIRMWARE_NAME:Marlin 1.1.0 From Archive SOURCE_CODE_URL:http:// ... PROTOCOL_VERSION:1.0 MACHINE_TYPE:www.cxsw3d.com EXTRUDER_COUNT:1 UUID:00000000-0000-0000-0000-000000000000",
            {
                "FIRMWARE_NAME": "Marlin 1.1.0 From Archive",
                "SOURCE_CODE_URL": "http:// ...",
                "PROTOCOL_VERSION": "1.0",
                "MACHINE_TYPE": "www.cxsw3d.com",
                "EXTRUDER_COUNT": "1",
                "UUID": "00000000-0000-0000-0000-000000000000",
            },
        ),
        # Test firmware name with time created
        (
            "FIRMWARE_NAME:Marlin 2.0.7.2 (Nov 27 2020 14:30:11) SOURCE_CODE_URL:https://github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:Ender 5 Pro EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff",
            {
                "FIRMWARE_NAME": "Marlin 2.0.7.2 (Nov 27 2020 14:30:11)",
                "SOURCE_CODE_URL": "https://github.com/MarlinFirmware/Marlin",
                "PROTOCOL_VERSION": "1.0",
                "MACHINE_TYPE": "Ender 5 Pro",
                "EXTRUDER_COUNT": "1",
                "UUID": "cede2a2f-41a2-4748-9b12-c55c62f367ff",
            },
        ),
        # Test that keys beginning with _ or number are ignored
        (
            "KEY1:VALUE1 _KEY2:INVALID 123:INVALID 1KEY:INVALID KEY2:VALUE2",
            {"KEY1": "VALUE1 _KEY2:INVALID 123:INVALID 1KEY:INVALID", "KEY2": "VALUE2"},
        ),
    )
    @unpack
    def test_parse_firmware_line(self, line, expected):
        from octoprint.util.comm import parse_firmware_line

        result = parse_firmware_line(line)
        self.assertDictEqual(expected, result)

    @data(
        ("Cap:EEPROM:1", ("EEPROM", True)),
        ("Cap:EEPROM:0", ("EEPROM", False)),
        ("AUTOREPORT_TEMP:1", ("AUTOREPORT_TEMP", True)),
        ("AUTOREPORT_TEMP:0", ("AUTOREPORT_TEMP", False)),
        ("TOO:MANY:FIELDS", None),
        ("Cap:", None),
        ("TOOLITTLEFIELDS", None),
        ("WRONG:FLAG", None),
    )
    @unpack
    def test_parse_capability_line(self, line, expected):
        from octoprint.util.comm import parse_capability_line

        result = parse_capability_line(line)
        self.assertEqual(expected, result)

    @data(
        ("Resend:23", 23),
        ("Resend: N23", 23),
        ("Resend: N:23", 23),
        ("rs 23", 23),
        ("rs N23", 23),
        ("rs N:23", 23),
        ("rs N23 expected checksum 109", 23),  # teacup, see #300
    )
    @unpack
    def test_parse_resend_line(self, line, expected):
        from octoprint.util.comm import parse_resend_line

        result = parse_resend_line(line)
        self.assertEqual(expected, result)

    @data(
        # Marlin
        (
            "ok X:62.417 Y:64.781 Z:0.2 E:2.72328 Count: A:6241 B:6478 C:20",
            {"x": 62.417, "y": 64.781, "z": 0.2, "e": 2.72328},
        ),
        (
            "X:62.417 Y:64.781 Z:0.2 E:2.72328 Count: A:6241 B:6478 C:20",
            {"x": 62.417, "y": 64.781, "z": 0.2, "e": 2.72328},
        ),
        # RepRapFirmware
        (
            "X:96.99 Y:88.31 Z:0.30 E0:0.0 E1:0.0 E2:0.0 E3:0.0 E4:0.0 E5:0.0",
            {
                "x": 96.99,
                "y": 88.31,
                "z": 0.3,
                "e0": 0.0,
                "e1": 0.0,
                "e2": 0.0,
                "e3": 0.0,
                "e4": 0.0,
                "e5": 0.0,
            },
        ),
        # whitespace after the :, e.g. AlfaWise U20, see #2839
        ("X:150.0 Y:150.0 Z:  0.7 E:  0.0", {"x": 150.0, "y": 150.0, "z": 0.7, "e": 0.0}),
        # invalid
        ("", None),
        ("X:62.417 Y:64.781 Z:0.2", None),
    )
    @unpack
    def test_parse_position_line(self, line, expected):
        from octoprint.util.comm import parse_position_line

        result = parse_position_line(line)
        if expected is None:
            self.assertIsNone(result)
        else:
            self.assertDictEqual(expected, result)


class TestPositionRecord(unittest.TestCase):
    def test_as_dict_regular(self):
        coords = {"x": 1, "y": 2, "z": 3, "e": 4}

        position = self._create_position(**coords)

        expected = dict(coords)
        expected.update({"f": None, "t": None})
        self.assertDictEqual(position.as_dict(), expected)

    def test_as_dict_extra_e(self):
        coords = {"x": 1, "y": 2, "z": 3, "e0": 4, "e1": 5}

        position = self._create_position(**coords)

        expected = dict(coords)
        expected.update({"e": None, "f": None, "t": None})
        self.assertDictEqual(position.as_dict(), expected)

    def test_copy_from_regular(self):
        coords = {"x": 1, "y": 2, "z": 3, "e": 4}
        position1 = self._create_position(**coords)
        position2 = self._create_position()

        position2.copy_from(position1)

        expected = dict(coords)
        expected.update({"f": None, "t": None})
        self.assertDictEqual(position2.as_dict(), expected)

    def test_copy_from_extra_e(self):
        coords = {"x": 1, "y": 2, "z": 3, "e0": 4, "e1": 5}
        position1 = self._create_position(**coords)
        position2 = self._create_position()

        position2.copy_from(position1)

        expected = dict(coords)
        expected.update({"e": None, "f": None, "t": None})
        self.assertDictEqual(position2.as_dict(), expected)

    def test_copy_from_extra_e_changed(self):
        coords1 = {"x": 1, "y": 2, "z": 3, "e0": 4, "e1": 5}
        position1 = self._create_position(**coords1)

        coords2 = {"x": 2, "y": 4, "z": 6, "e0": 8, "e1": 10, "e2": 12}
        position2 = self._create_position(**coords2)

        expected_before = dict(coords2)
        expected_before.update({"e": None, "f": None, "t": None})
        self.assertDictEqual(position2.as_dict(), expected_before)

        position2.copy_from(position1)

        expected_after = dict(coords1)
        expected_after.update({"e": None, "f": None, "t": None})
        self.assertDictEqual(position2.as_dict(), expected_after)

    def _create_position(self, **kwargs):
        from octoprint.util.comm import PositionRecord

        return PositionRecord(**kwargs)


@ddt
class TestTemperatureRecord(unittest.TestCase):
    @data("TX", "B2", "BX", "SOMETHING_CUSTOM", "1234B456", "blub", "fnord", "C1", "CX")
    def test_set_custom(self, identifier):
        temperature = self._create_temperature()

        temperature.set_custom(identifier, 1, 2)

        self.assertTrue(identifier in temperature.custom)

    @data("T", "T1", "T42", "B", "C")
    def test_set_custom_reserved(self, identifier):
        temperature = self._create_temperature()

        try:
            temperature.set_custom(identifier, 1, 2)
            self.fail(f"Expected ValueError for reserved identifier {identifier}")
        except ValueError as ex:
            self.assertTrue("is a reserved identifier" in str(ex))

    def _create_temperature(self, **kwargs):
        from octoprint.util.comm import TemperatureRecord

        return TemperatureRecord(**kwargs)
