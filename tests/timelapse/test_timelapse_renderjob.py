# coding=utf-8
from __future__ import absolute_import

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"

import unittest

from ddt import ddt, data, unpack

from octoprint.timelapse import TimelapseRenderJob

@ddt
class TimelapseRenderJobTest(unittest.TestCase):

	@data(
		(("/path/to/ffmpeg", 25, "10000k", 1, "/path/to/input/files_%d.jpg", "/path/to/output.mpg"),
		 dict(),
		 '/path/to/ffmpeg -framerate 25 -loglevel error -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -r 25 -y -b 10000k -f vob -vf \'[in] format=yuv420p [out]\' "/path/to/output.mpg"'),

		(("/path/to/ffmpeg", 25, "10000k", 1, "/path/to/input/files_%d.jpg", "/path/to/output.mpg"),
		 dict(hflip=True),
		 '/path/to/ffmpeg -framerate 25 -loglevel error -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -r 25 -y -b 10000k -f vob -vf \'[in] format=yuv420p,hflip [out]\' "/path/to/output.mpg"'),

		(("/path/to/ffmpeg", 25, "20000k", 4, "/path/to/input/files_%d.jpg", "/path/to/output.mpg"),
		 dict(rotate=True, watermark="/path/to/watermark.png"),
		 '/path/to/ffmpeg -framerate 25 -loglevel error -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 4 -r 25 -y -b 20000k -f vob -vf \'[in] format=yuv420p,transpose=2 [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]\' "/path/to/output.mpg"')
	)
	@unpack
	def test_create_ffmpeg_command_string(self, args, kwargs, expected):
		actual = TimelapseRenderJob._create_ffmpeg_command_string(*args, **kwargs)
		self.assertEquals(actual, expected)

	@data(
		(dict(),
		 '[in] format=yuv420p [out]'),

		(dict(pixfmt="test"),
		 '[in] format=test [out]'),

		(dict(hflip=True),
		 '[in] format=yuv420p,hflip [out]'),

		(dict(vflip=True),
		 '[in] format=yuv420p,vflip [out]'),

		(dict(rotate=True),
		 '[in] format=yuv420p,transpose=2 [out]'),

		(dict(vflip=True, rotate=True),
		 '[in] format=yuv420p,vflip,transpose=2 [out]'),

		(dict(vflip=True, hflip=True, rotate=True),
		 '[in] format=yuv420p,hflip,vflip,transpose=2 [out]'),

		(dict(watermark="/path/to/watermark.png"),
		 '[in] format=yuv420p [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]'),

		(dict(hflip=True, watermark="/path/to/watermark.png"),
		 '[in] format=yuv420p,hflip [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]'),

	)
	@unpack
	def test_create_filter_string(self, kwargs, expected):
		actual = TimelapseRenderJob._create_filter_string(**kwargs)
		self.assertEquals(actual, expected)
