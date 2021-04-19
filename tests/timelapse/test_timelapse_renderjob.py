__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

from ddt import data, ddt, unpack

from octoprint.timelapse import TimelapseRenderJob


@ddt
class TimelapseRenderJobTest(unittest.TestCase):
    @data(
        (
            (
                '{ffmpeg} -r {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b {bitrate} -f {containerformat} -y {filters} "{output}"',
                "/path/to/ffmpeg",
                25,
                "10000k",
                1,
                "/path/to/input/files_%d.jpg",
                "/path/to/output.mpg",
                "mpeg2video",
            ),
            {},
            '/path/to/ffmpeg -r 25 -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -b 10000k -f vob -y -vf \'[in] format=yuv420p [out]\' "/path/to/output.mpg"',
        ),
        (
            (
                '{ffmpeg} -r {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b {bitrate} -f {containerformat} -y -g 5 {filters} "{output}"',
                "/path/to/ffmpeg",
                25,
                "10000k",
                1,
                "/path/to/input/files_%d.jpg",
                "/path/to/output.mpg",
                "mpeg2video",
            ),
            {},
            '/path/to/ffmpeg -r 25 -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -b 10000k -f vob -y -g 5 -vf \'[in] format=yuv420p [out]\' "/path/to/output.mpg"',
        ),
        (
            (
                '{ffmpeg} -r {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b {bitrate} -f {containerformat} -y {filters} "{output}"',
                "/path/to/ffmpeg",
                25,
                "10000k",
                1,
                "/path/to/input/files_%d.jpg",
                "/path/to/output.mp4",
                "libx264",
            ),
            {},
            '/path/to/ffmpeg -r 25 -i "/path/to/input/files_%d.jpg" -vcodec libx264 -threads 1 -b 10000k -f mp4 -y -vf \'[in] format=yuv420p [out]\' "/path/to/output.mp4"',
        ),
        (
            (
                '{ffmpeg} -r {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b {bitrate} -f {containerformat} -y {filters} "{output}"',
                "/path/to/ffmpeg",
                25,
                "10000k",
                1,
                "/path/to/input/files_%d.jpg",
                "/path/to/output.mpg",
                "mpeg2video",
            ),
            {"hflip": True},
            '/path/to/ffmpeg -r 25 -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -b 10000k -f vob -y -vf \'[in] format=yuv420p,hflip [out]\' "/path/to/output.mpg"',
        ),
        (
            (
                '{ffmpeg} -r {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b {bitrate} -f {containerformat} -y {filters} "{output}"',
                "/path/to/ffmpeg",
                25,
                "20000k",
                4,
                "/path/to/input/files_%d.jpg",
                "/path/to/output.mpg",
                "mpeg2video",
            ),
            {"rotate": True, "watermark": "/path/to/watermark.png"},
            '/path/to/ffmpeg -r 25 -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 4 -b 20000k -f vob -y -vf \'[in] format=yuv420p,transpose=2 [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]\' "/path/to/output.mpg"',
        ),
    )
    @unpack
    def test_create_ffmpeg_command_string(self, args, kwargs, expected):
        actual = TimelapseRenderJob._create_ffmpeg_command_string(*args, **kwargs)
        self.assertEqual(expected, actual)

    @data(
        ({}, "[in] format=yuv420p [out]"),
        ({"pixfmt": "test"}, "[in] format=test [out]"),
        ({"hflip": True}, "[in] format=yuv420p,hflip [out]"),
        ({"vflip": True}, "[in] format=yuv420p,vflip [out]"),
        ({"rotate": True}, "[in] format=yuv420p,transpose=2 [out]"),
        ({"vflip": True, "rotate": True}, "[in] format=yuv420p,vflip,transpose=2 [out]"),
        (
            {"vflip": True, "hflip": True, "rotate": True},
            "[in] format=yuv420p,hflip,vflip,transpose=2 [out]",
        ),
        (
            {"watermark": "/path/to/watermark.png"},
            "[in] format=yuv420p [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]",
        ),
        (
            {"hflip": True, "watermark": "/path/to/watermark.png"},
            "[in] format=yuv420p,hflip [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]",
        ),
    )
    @unpack
    def test_create_filter_string(self, kwargs, expected):
        actual = TimelapseRenderJob._create_filter_string(**kwargs)
        self.assertEqual(actual, expected)
