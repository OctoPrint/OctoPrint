# coding=utf-8

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import logging
import os
import threading
import time
import fnmatch
import datetime
import sys
import shutil
import Queue
import requests

import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager, Events
import sarge

# currently configured timelapse
current = None


def getFinishedTimelapses():
	files = []
	basedir = settings().getBaseFolder("timelapse")
	for osFile in os.listdir(basedir):
		if not fnmatch.fnmatch(osFile, "*.mpg"):
			continue
		statResult = os.stat(os.path.join(basedir, osFile))
		files.append({
			"name": osFile,
			"size": util.get_formatted_size(statResult.st_size),
			"bytes": statResult.st_size,
			"date": util.get_formatted_datetime(datetime.datetime.fromtimestamp(statResult.st_ctime))
		})
	return files

validTimelapseTypes = ["off", "timed", "zchange"]

updateCallbacks = []


def registerCallback(callback):
	if not callback in updateCallbacks:
		updateCallbacks.append(callback)


def unregisterCallback(callback):
	if callback in updateCallbacks:
		updateCallbacks.remove(callback)


def notifyCallbacks(timelapse):
	if timelapse is None:
		config = None
	else:
		config = timelapse.config_data()
	for callback in updateCallbacks:
		try: callback.sendTimelapseConfig(config)
		except: logging.getLogger(__name__).exception("Exception while pushing timelapse configuration")


def configureTimelapse(config=None, persist=False):
	global current

	if config is None:
		config = settings().get(["webcam", "timelapse"])

	if current is not None:
		current.unload()

	type = config["type"]

	postRoll = 0
	if "postRoll" in config and config["postRoll"] >= 0:
		postRoll = config["postRoll"]

	fps = 25
	if "fps" in config and config["fps"] > 0:
		fps = config["fps"]

	if type is None or "off" == type:
		current = None
	elif "zchange" == type:
		retractionZHop = 0
                if "options" in config and "retractionZHop" in config["options"] and config["options"]["retractionZHop"] > 0:
                        retractionZHop = config["options"]["retractionZHop"]
		current = ZTimelapse(post_roll=postRoll, retraction_zhop=retractionZHop, fps=fps)
	elif "timed" == type:
		interval = 10
		if "options" in config and "interval" in config["options"] and config["options"]["interval"] > 0:
			interval = config["options"]["interval"]
		current = TimedTimelapse(post_roll=postRoll, interval=interval, fps=fps)

	notifyCallbacks(current)

	if persist:
		settings().set(["webcam", "timelapse"], config)
		settings().save()


class Timelapse(object):
	QUEUE_ENTRY_TYPE_CAPTURE = "capture"
	QUEUE_ENTRY_TYPE_CALLBACK = "callback"

	def __init__(self, post_roll=0, fps=25):
		self._logger = logging.getLogger(__name__)
		self._image_number = None
		self._in_timelapse = False
		self._gcode_file = None

		self._post_roll = post_roll
		self._on_post_roll_done = None

		self._capture_dir = settings().getBaseFolder("timelapse_tmp")
		self._movie_dir = settings().getBaseFolder("timelapse")
		self._snapshot_url = settings().get(["webcam", "snapshot"])
		self._ffmpeg_threads = settings().get(["webcam", "ffmpegThreads"])

		self._fps = fps

		self._render_thread = None

		self._capture_mutex = threading.Lock()
		self._capture_queue = Queue.Queue()
		self._capture_queue_active = True

		self._capture_queue_thread = threading.Thread(target=self._capture_queue_worker)
		self._capture_queue_thread.daemon = True
		self._capture_queue_thread.start()

		# subscribe events
		eventManager().subscribe(Events.PRINT_STARTED, self.on_print_started)
		eventManager().subscribe(Events.PRINT_FAILED, self.on_print_done)
		eventManager().subscribe(Events.PRINT_DONE, self.on_print_done)
		eventManager().subscribe(Events.PRINT_RESUMED, self.on_print_resumed)
		for (event, callback) in self.event_subscriptions():
			eventManager().subscribe(event, callback)

	@property
	def post_roll(self):
		return self._post_roll

	@property
	def fps(self):
		return self._fps

	def unload(self):
		if self._in_timelapse:
			self.stop_timelapse(doCreateMovie=False)

		# unsubscribe events
		eventManager().unsubscribe(Events.PRINT_STARTED, self.on_print_started)
		eventManager().unsubscribe(Events.PRINT_FAILED, self.on_print_done)
		eventManager().unsubscribe(Events.PRINT_DONE, self.on_print_done)
		eventManager().unsubscribe(Events.PRINT_RESUMED, self.on_print_resumed)
		for (event, callback) in self.event_subscriptions():
			eventManager().unsubscribe(event, callback)

	def on_print_started(self, event, payload):
		"""
		Override this to perform additional actions upon start of a print job.
		"""
		self.start_timelapse(payload["file"])

	def on_print_done(self, event, payload):
		"""
		Override this to perform additional actions upon the stop of a print job.
		"""
		self.stop_timelapse(success=(event==Events.PRINT_DONE))

	def on_print_resumed(self, event, payload):
		"""
		Override this to perform additional actions upon the pausing of a print job.
		"""
		if not self._in_timelapse:
			self.start_timelapse(payload["file"])

	def event_subscriptions(self):
		"""
		Override this method to subscribe to additional events by returning an array of (event, callback) tuples.

		Events that are already subscribed:
		  * PrintStarted - self.onPrintStarted
		  * PrintResumed - self.onPrintResumed
		  * PrintFailed - self.onPrintDone
		  * PrintDone - self.onPrintDone
		"""
		return []

	def config_data(self):
		"""
		Override this method to return the current timelapse configuration data. The data should have the following
		form:

		    type: "<type of timelapse>",
		    options: { <additional options> }
		"""
		return None

	def start_timelapse(self, gcodeFile):
		self._logger.debug("Starting timelapse for %s" % gcodeFile)
		self.clean_capture_dir()

		self._image_number = 0
		self._in_timelapse = True
		self._gcode_file = os.path.basename(gcodeFile)

	def stop_timelapse(self, doCreateMovie=True, success=True):
		self._logger.debug("Stopping timelapse")

		self._in_timelapse = False

		def resetImageNumber():
			self._image_number = None

		def createMovie():
			self._render_thread = threading.Thread(target=self._create_movie, kwargs={"success": success})
			self._render_thread.daemon = True
			self._render_thread.start()

		def resetAndCreate():
			resetImageNumber()
			createMovie()

		def waitForCaptures(callback):
			self._capture_queue.put(dict(type=self.__class__.QUEUE_ENTRY_TYPE_CALLBACK, callback=callback))

		def getWaitForCaptures(callback):
			def f():
				waitForCaptures(callback)
			return f

		if self._post_roll > 0:
			eventManager().fire(Events.POSTROLL_START, dict(postroll_duration=self.calculate_post_roll(), postroll_length=self.post_roll, postroll_fps=self.fps))
			self._post_roll_start = time.time()
			if doCreateMovie:
				self._on_post_roll_done = getWaitForCaptures(resetAndCreate)
			else:
				self._on_post_roll_done = resetImageNumber
			self.process_post_roll()
		else:
			self._post_roll_start = None
			if doCreateMovie:
				waitForCaptures(resetAndCreate)
			else:
				resetImageNumber()

	def calculate_post_roll(self):
		return None

	def process_post_roll(self):
		self.post_roll_finished()

	def post_roll_finished(self):
		if self.post_roll:
			eventManager().fire(Events.POSTROLL_END)
			if self._on_post_roll_done is not None:
				self._on_post_roll_done()

	def captureImage(self):
		if self._capture_dir is None:
			self._logger.warn("Cannot capture image, capture directory is unset")
			return

		with self._capture_mutex:
			if self._image_number is None:
				self._logger.warn("Cannot capture image, image number is unset")
				return

			filename = os.path.join(self._capture_dir, "tmp_%05d.jpg" % self._image_number)
			self._image_number += 1

		self._logger.debug("Capturing image to %s" % filename)
		entry = dict(type=self.__class__.QUEUE_ENTRY_TYPE_CAPTURE,
		             filename=filename,
		             onerror=self._on_capture_error)
		self._capture_queue.put(entry)
		return filename

	def _on_capture_error(self):
		with self._capture_mutex:
			if self._image_number is not None and self._image_number > 0:
				self._image_number -= 1

	def _capture_queue_worker(self):
		while self._capture_queue_active:
			entry = self._capture_queue.get(block=True)

			if entry["type"] == self.__class__.QUEUE_ENTRY_TYPE_CAPTURE and "filename" in entry:
				filename = entry["filename"]
				onerror = entry.pop("onerror", None)
				self._perform_capture(filename, onerror=onerror)

			elif entry["type"] == self.__class__.QUEUE_ENTRY_TYPE_CALLBACK and "callback" in entry:
				args = entry.pop("args", [])
				kwargs = entry.pop("kwargs", dict())
				entry["callback"](*args, **kwargs)

	def _perform_capture(self, filename, onerror=None):
		eventManager().fire(Events.CAPTURE_START, {"file": filename})
		try:
			self._logger.debug("Going to capture %s from %s" % (filename, self._snapshot_url))
			r = requests.get(self._snapshot_url, stream=True)
			with open (filename, "wb") as f:
				for chunk in r.iter_content(chunk_size=1024):
					if chunk:
						f.write(chunk)
						f.flush()
			self._logger.debug("Image %s captured from %s" % (filename, self._snapshot_url))
		except:
			self._logger.exception("Could not capture image %s from %s" % (filename, self._snapshot_url))
			if callable(onerror):
				onerror()
			eventManager().fire(Events.CAPTURE_FAILED, {"file": filename})
			return False
		else:
			eventManager().fire(Events.CAPTURE_DONE, {"file": filename})
			return True

	def _create_movie(self, success=True):
		ffmpeg = settings().get(["webcam", "ffmpeg"])
		bitrate = settings().get(["webcam", "bitrate"])
		if ffmpeg is None or bitrate is None:
			self._logger.warn("Cannot create movie, path to ffmpeg or desired bitrate is unset")
			return

		input = os.path.join(self._capture_dir, "tmp_%05d.jpg")
		if success:
			output = os.path.join(self._movie_dir, "%s_%s.mpg" % (os.path.splitext(self._gcode_file)[0], time.strftime("%Y%m%d%H%M%S")))
		else:
			output = os.path.join(self._movie_dir, "%s_%s-failed.mpg" % (os.path.splitext(self._gcode_file)[0], time.strftime("%Y%m%d%H%M%S")))

		# prepare ffmpeg command
		command = [
			ffmpeg, '-framerate', str(self._fps), '-loglevel', 'error', '-i', input, '-vcodec', 'mpeg2video', '-threads', str(self._ffmpeg_threads), '-pix_fmt', 'yuv420p', '-r', str(self._fps), '-y', '-b', bitrate,
			'-f', 'vob']

		filters = []

		# flip video if configured
		if settings().getBoolean(["webcam", "flipH"]):
			filters.append('hflip')
		if settings().getBoolean(["webcam", "flipV"]):
			filters.append('vflip')
		if settings().getBoolean(["webcam", "rotate90"]):
			filters.append('transpose=2')

		# add watermark if configured
		watermarkFilter = None
		if settings().getBoolean(["webcam", "watermark"]):
			watermark = os.path.join(os.path.dirname(__file__), "static", "img", "watermark.png")
			if sys.platform == "win32":
				# Because ffmpeg hiccups on windows' drive letters and backslashes we have to give the watermark
				# path a special treatment. Yeah, I couldn't believe it either...
				watermark = watermark.replace("\\", "/").replace(":", "\\\\:")

			watermarkFilter = "movie=%s [wm]; [%%(inputName)s][wm] overlay=10:main_h-overlay_h-10" % watermark

		filterstring = None
		if len(filters) > 0:
			if watermarkFilter is not None:
				filterstring = "[in] %s [postprocessed]; %s [out]" % (",".join(filters), watermarkFilter % {"inputName": "postprocessed"})
			else:
				filterstring = "[in] %s [out]" % ",".join(filters)
		elif watermarkFilter is not None:
			filterstring = watermarkFilter % {"inputName": "in"} + " [out]"

		if filterstring is not None:
			self._logger.debug("Applying videofilter chain: %s" % filterstring)
			command.extend(["-vf", sarge.shell_quote(filterstring)])

		# finalize command with output file
		self._logger.debug("Rendering movie to %s" % output)
		command.append("\"" + output + "\"")
		eventManager().fire(Events.MOVIE_RENDERING, {"gcode": self._gcode_file, "movie": output, "movie_basename": os.path.basename(output)})

		command_str = " ".join(command)
		self._logger.debug("Executing command: %s" % command_str)

		try:
			p = sarge.run(command_str, stderr=sarge.Capture())
			if p.returncode == 0:
				eventManager().fire(Events.MOVIE_DONE, {"gcode": self._gcode_file, "movie": output, "movie_basename": os.path.basename(output)})
			else:
				returncode = p.returncode
				stderr_text = p.stderr.text
				self._logger.warn("Could not render movie, got return code %r: %s" % (returncode, stderr_text))
				eventManager().fire(Events.MOVIE_FAILED, {"gcode": self._gcode_file, "movie": output, "movie_basename": os.path.basename(output), "returncode": returncode, "error": stderr_text})
		except:
			self._logger.exception("Could not render movie due to unknown error")
			eventManager().fire(Events.MOVIE_FAILED, {"gcode": self._gcode_file, "movie": output, "movie_basename": os.path.basename(output), "returncode": 255, "error": "Unknown error"})

	def clean_capture_dir(self):
		if not os.path.isdir(self._capture_dir):
			self._logger.warn("Cannot clean capture directory, it is unset")
			return

		for filename in os.listdir(self._capture_dir):
			if not fnmatch.fnmatch(filename, "*.jpg"):
				continue
			os.remove(os.path.join(self._capture_dir, filename))


class ZTimelapse(Timelapse):
	def __init__(self, post_roll=0, retraction_zhop=0, fps=25):
		Timelapse.__init__(self, post_roll=post_roll, fps=fps)
		self._retraction_zhop = retraction_zhop
		self._logger.debug("ZTimelapse initialized")

	@property
	def retraction_zhop(self):
                return self._retraction_zhop

	def event_subscriptions(self):
		return [
			(Events.Z_CHANGE, self._on_z_change)
		]

	def config_data(self):
		return {
			"type": "zchange",
			"options": {
				"retractionZHop": self._retraction_zhop
			}
		}

	def process_post_roll(self):
		with self._capture_mutex:
			filename = os.path.join(self._capture_dir, "tmp_%05d.jpg" % self._image_number)
			self._image_number += 1

		if self._perform_capture(filename):
			for _ in range(self._post_roll * self._fps):
				newFile = os.path.join(self._capture_dir, "tmp_%05d.jpg" % self._image_number)
				self._image_number += 1
				shutil.copyfile(filename, newFile)

		Timelapse.process_post_roll(self)

	def _on_z_change(self, event, payload):
		diff = round(payload["new"] - payload["old"], 3)
		zhop = round(self._retraction_zhop, 3)
		if diff > 0 and diff != zhop:
			self.captureImage()


class TimedTimelapse(Timelapse):
	def __init__(self, post_roll=0, interval=1, fps=25):
		Timelapse.__init__(self, post_roll=post_roll, fps=fps)
		self._interval = interval
		if self._interval < 1:
			self._interval = 1 # force minimum interval of 1s
		self._postroll_captures = 0
		self._timer = None
		self._logger.debug("TimedTimelapse initialized")

	@property
	def interval(self):
		return self._interval

	def config_data(self):
		return {
			"type": "timed",
			"options": {
				"interval": self._interval
			}
		}

	def on_print_started(self, event, payload):
		Timelapse.on_print_started(self, event, payload)
		if self._timer is not None:
			return

		self._logger.debug("Starting timer for interval based timelapse")
		from octoprint.util import RepeatedTimer
		self._timer = RepeatedTimer(self._interval, self._timer_task,
		                            run_first=True, condition=self._timer_active,
		                            on_finish=self._on_timer_finished)
		self._timer.start()

	def on_print_done(self, event, payload):
		self._postroll_captures = self.post_roll * self.fps
		Timelapse.on_print_done(self, event, payload)

	def calculate_post_roll(self):
		return self.post_roll * self.fps * self.interval

	def process_post_roll(self):
		pass

	def post_roll_finished(self):
		Timelapse.post_roll_finished(self)
		self._timer = None

	def _timer_active(self):
		return self._in_timelapse or self._postroll_captures > 0

	def _timer_task(self):
		self.captureImage()
		if self._postroll_captures > 0:
			self._postroll_captures -= 1

	def _on_timer_finished(self):
		self.post_roll_finished()
