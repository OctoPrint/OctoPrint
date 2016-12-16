# coding=utf-8
from __future__ import absolute_import, division, print_function
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
try:
	import queue
except ImportError:
	import Queue as queue
import requests

import octoprint.util as util

from octoprint.settings import settings
from octoprint.events import eventManager, Events

import sarge
import collections

import re

try:
	from os import scandir, walk
except ImportError:
	from scandir import scandir, walk


# currently configured timelapse
current = None

# currently active render job, if any
current_render_job = None

# filename formats
_capture_format = "{prefix}-%d.jpg"
_output_format = "{prefix}.mpg"

# old capture format, needed to delete old left-overs from
# versions <1.2.9
_old_capture_format_re = re.compile("^tmp_\d{5}.jpg$")

# valid timelapses
_valid_timelapse_types = ["off", "timed", "zchange"]

# callbacks for timelapse config updates
_update_callbacks = []

# lock for timelapse cleanup, must be re-entrant
_cleanup_lock = threading.RLock()

# lock for timelapse job
_job_lock = threading.RLock()


def _extract_prefix(filename):
	"""
	>>> _extract_prefix("some_long_filename_without_hyphen.jpg")
	>>> _extract_prefix("-first_char_is_hyphen.jpg")
	>>> _extract_prefix("some_long_filename_with-stuff.jpg")
	'some_long_filename_with'
	"""
	pos = filename.rfind("-")
	if not pos or pos < 0:
		return None
	return filename[:pos]


def last_modified_finished():
	return os.stat(settings().getBaseFolder("timelapse")).st_mtime


def last_modified_unrendered():
	return os.stat(settings().getBaseFolder("timelapse_tmp")).st_mtime


def get_finished_timelapses():
	files = []
	basedir = settings().getBaseFolder("timelapse")
	for entry in scandir(basedir):
		if not fnmatch.fnmatch(entry.name, "*.mp[g4]"):
			continue
		files.append({
			"name": entry.name,
			"size": util.get_formatted_size(entry.stat().st_size),
			"bytes": entry.stat().st_size,
			"date": util.get_formatted_datetime(datetime.datetime.fromtimestamp(entry.stat().st_ctime))
		})
	return files


def get_unrendered_timelapses():
	global _job_lock
	global current

	delete_old_unrendered_timelapses()

	basedir = settings().getBaseFolder("timelapse_tmp")
	jobs = collections.defaultdict(lambda: dict(count=0, size=None, bytes=0, date=None, timestamp=None))

	for entry in scandir(basedir):
		if not fnmatch.fnmatch(entry.name, "*.jpg"):
			continue

		prefix = _extract_prefix(entry.name)
		if prefix is None:
			continue

		jobs[prefix]["count"] += 1
		jobs[prefix]["bytes"] += entry.stat().st_size
		if jobs[prefix]["timestamp"] is None or entry.stat().st_ctime < jobs[prefix]["timestamp"]:
			jobs[prefix]["timestamp"] = entry.stat().st_ctime

	with _job_lock:
		global current_render_job

		def finalize_fields(prefix, job):
			currently_recording = current is not None and current.prefix == prefix
			currently_rendering = current_render_job is not None and current_render_job["prefix"] == prefix

			job["size"] = util.get_formatted_size(job["bytes"])
			job["date"] = util.get_formatted_datetime(datetime.datetime.fromtimestamp(job["timestamp"]))
			job["recording"] = currently_recording
			job["rendering"] = currently_rendering
			job["processing"] = currently_recording or currently_rendering
			del job["timestamp"]

			return job

		return sorted([util.dict_merge(dict(name=key), finalize_fields(key, value)) for key, value in jobs.items()], key=lambda x: x["name"])


def delete_unrendered_timelapse(name):
	global _cleanup_lock

	basedir = settings().getBaseFolder("timelapse_tmp")
	with _cleanup_lock:
		for entry in scandir(basedir):
			try:
				if fnmatch.fnmatch(entry.name, "{}*.jpg".format(name)):
					os.remove(entry.path)
			except:
				if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
					logging.getLogger(__name__).exception("Error while processing file {} during cleanup".format(entry.name))


def render_unrendered_timelapse(name, gcode=None, postfix=None, fps=25):
	capture_dir = settings().getBaseFolder("timelapse_tmp")
	output_dir = settings().getBaseFolder("timelapse")
	threads = settings().get(["webcam", "ffmpegThreads"])

	job = TimelapseRenderJob(capture_dir, output_dir, name,
	                         postfix=postfix,
	                         capture_format=_capture_format,
	                         output_format=_output_format,
	                         fps=fps,
	                         threads=threads,
	                         on_start=_create_render_start_handler(name, gcode=gcode),
	                         on_success=_create_render_success_handler(name, gcode=gcode),
	                         on_fail=_create_render_fail_handler(name, gcode=gcode),
	                         on_always=_create_render_always_handler(name, gcode=gcode))
	job.process()


def delete_old_unrendered_timelapses():
	global _cleanup_lock

	basedir = settings().getBaseFolder("timelapse_tmp")
	clean_after_days = settings().getInt(["webcam", "cleanTmpAfterDays"])
	cutoff = time.time() - clean_after_days * 24 * 60 * 60

	prefixes_to_clean = []

	with _cleanup_lock:
		for entry in scandir(basedir):
			try:
				prefix = _extract_prefix(entry.name)
				if prefix is None:
					# might be an old tmp_00000.jpg kinda frame. we can't
					# render those easily anymore, so delete that stuff
					if _old_capture_format_re.match(entry.name):
						os.remove(entry.path)
					continue

				if prefix in prefixes_to_clean:
					continue

				if entry.stat().st_mtime < cutoff:
					prefixes_to_clean.append(prefix)
			except:
				if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
					logging.getLogger(__name__).exception("Error while processing file {} during cleanup".format(entry.name))

		for prefix in prefixes_to_clean:
			delete_unrendered_timelapse(prefix)
			logging.getLogger(__name__).info("Deleted old unrendered timelapse {}".format(prefix))


def _create_render_start_handler(name, gcode=None):
	def f(movie):
		global _job_lock

		with _job_lock:
			global current_render_job
			payload = dict(gcode=gcode if gcode is not None else "unknown",
			               movie=movie,
			               movie_basename=os.path.basename(movie),
			               movie_prefix=name)
			current_render_job = dict(prefix=name)
			current_render_job.update(payload)
		eventManager().fire(Events.MOVIE_RENDERING, payload)
	return f


def _create_render_success_handler(name, gcode=None):
	def f(movie):
		delete_unrendered_timelapse(name)
		payload = dict(gcode=gcode if gcode is not None else "unknown",
		               movie=movie,
		               movie_basename=os.path.basename(movie),
		               movie_prefix=name)
		eventManager().fire(Events.MOVIE_DONE, payload)
	return f


def _create_render_fail_handler(name, gcode=None):
	def f(movie, returncode=255, stdout="Unknown error", stderr="Unknown error", reason="unknown"):
		payload = dict(gcode=gcode if gcode is not None else "unknown",
		               movie=movie,
		               movie_basename=os.path.basename(movie),
		               movie_prefix=name,
		               returncode=returncode,
		               out=stdout,
		               error=stderr,
		               reason=reason)
		eventManager().fire(Events.MOVIE_FAILED, payload)
	return f


def _create_render_always_handler(name, gcode=None):
	def f(movie):
		global current_render_job
		global _job_lock
		with _job_lock:
			current_render_job = None
	return f


def register_callback(callback):
	if not callback in _update_callbacks:
		_update_callbacks.append(callback)


def unregister_callback(callback):
	if callback in _update_callbacks:
		_update_callbacks.remove(callback)


def notify_callbacks(timelapse):
	if timelapse is None:
		config = None
	else:
		config = timelapse.config_data()
	for callback in _update_callbacks:
		try: callback.sendTimelapseConfig(config)
		except: logging.getLogger(__name__).exception("Exception while pushing timelapse configuration")


def configure_timelapse(config=None, persist=False):
	global current

	if config is None:
		config = settings().get(["webcam", "timelapse"], merged=True)

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
		capture_post_roll = True
		if "options" in config and "capturePostRoll" in config["options"] and isinstance(config["options"]["capturePostRoll"], bool):
			capture_post_roll = config["options"]["capturePostRoll"]
		current = TimedTimelapse(post_roll=postRoll, interval=interval, fps=fps, capture_post_roll=capture_post_roll)

	notify_callbacks(current)

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
		self._file_prefix = None

		self._capture_errors = 0
		self._capture_success = 0

		self._post_roll = post_roll
		self._post_roll_start = None
		self._on_post_roll_done = None

		self._capture_dir = settings().getBaseFolder("timelapse_tmp")
		self._movie_dir = settings().getBaseFolder("timelapse")
		self._snapshot_url = settings().get(["webcam", "snapshot"])

		self._fps = fps

		self._capture_mutex = threading.Lock()
		self._capture_queue = queue.Queue()
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
	def prefix(self):
		return self._file_prefix

	@property
	def post_roll(self):
		return self._post_roll

	@property
	def fps(self):
		return self._fps

	def unload(self):
		if self._in_timelapse:
			self.stop_timelapse(do_create_movie=False)

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

		self._image_number = 0
		self._capture_errors = 0
		self._capture_success = 0
		self._in_timelapse = True
		self._gcode_file = os.path.basename(gcodeFile)
		self._file_prefix = "{}_{}".format(os.path.splitext(self._gcode_file)[0], time.strftime("%Y%m%d%H%M%S"))

	def stop_timelapse(self, do_create_movie=True, success=True):
		self._logger.debug("Stopping timelapse")

		self._in_timelapse = False

		def reset_image_number():
			self._image_number = None

		def create_movie():
			render_unrendered_timelapse(self._file_prefix,
			                            gcode=self._gcode_file,
			                            postfix=None if success else "-fail",
			                            fps=self._fps)

		def reset_and_create():
			reset_image_number()
			create_movie()

		def wait_for_captures(callback):
			self._capture_queue.put(dict(type=self.__class__.QUEUE_ENTRY_TYPE_CALLBACK, callback=callback))

		def create_wait_for_captures(callback):
			def f():
				wait_for_captures(callback)
			return f

		# wait for everything so far in the queue to be processed, then see if we should process from there
		def continue_rendering():
			if self._capture_success == 0:
				# no images - either nothing was attempted to be captured or all attempts ran into an error
				if self._capture_errors > 0:
					# this is the latter case
					_create_render_fail_handler(self._file_prefix,
					                            gcode=self._gcode_file)("n/a",
					                                                    returncode=0,
					                                                    stdout="",
					                                                    stderr="",
					                                                    reason="no_frames")

				# in any case, don't continue
				return

			# check if we have post roll configured
			if self._post_roll > 0:
				# capture post roll, wait for THAT to finish, THEN render
				eventManager().fire(Events.POSTROLL_START,
				                    dict(postroll_duration=self.calculate_post_roll(),
				                         postroll_length=self.post_roll,
				                         postroll_fps=self.fps))
				self._post_roll_start = time.time()
				if do_create_movie:
					self._on_post_roll_done = create_wait_for_captures(reset_and_create)
				else:
					self._on_post_roll_done = reset_image_number
				self.process_post_roll()
			else:
				# no post roll? perfect, render
				self._post_roll_start = None
				if do_create_movie:
					wait_for_captures(reset_and_create)
				else:
					reset_image_number()

		self._logger.debug("Waiting to process capture queue")
		wait_for_captures(continue_rendering)

	def calculate_post_roll(self):
		return None

	def process_post_roll(self):
		self.post_roll_finished()

	def post_roll_finished(self):
		if self.post_roll:
			eventManager().fire(Events.POSTROLL_END)
			if self._on_post_roll_done is not None:
				self._on_post_roll_done()

	def capture_image(self):
		if self._capture_dir is None:
			self._logger.warn("Cannot capture image, capture directory is unset")
			return

		with self._capture_mutex:
			if self._image_number is None:
				self._logger.warn("Cannot capture image, image number is unset")
				return

			filename = os.path.join(self._capture_dir, _capture_format.format(prefix=self._file_prefix) % self._image_number)
			self._image_number += 1

		self._logger.debug("Capturing image to {}".format(filename))
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
		eventManager().fire(Events.CAPTURE_START, dict(file=filename))
		try:
			self._logger.debug("Going to capture {} from {}".format(filename, self._snapshot_url))
			r = requests.get(self._snapshot_url, stream=True)
			r.raise_for_status()

			with open (filename, "wb") as f:
				for chunk in r.iter_content(chunk_size=1024):
					if chunk:
						f.write(chunk)
						f.flush()

			self._logger.debug("Image {} captured from {}".format(filename, self._snapshot_url))
		except Exception as e:
			self._logger.exception("Could not capture image {} from {}".format(filename, self._snapshot_url))
			if callable(onerror):
				onerror()
			eventManager().fire(Events.CAPTURE_FAILED, dict(file=filename,
			                                                error=str(e),
			                                                url=self._snapshot_url))
			self._capture_errors += 1
			return False
		else:
			eventManager().fire(Events.CAPTURE_DONE, dict(file=filename))
			self._capture_success += 1
			return True

	def _copying_postroll(self):
		with self._capture_mutex:
			filename = os.path.join(self._capture_dir,
			                        _capture_format.format(prefix=self._file_prefix) % self._image_number)
			self._image_number += 1

		if self._perform_capture(filename):
			for _ in range(self._post_roll * self._fps):
				newFile = os.path.join(self._capture_dir,
				                       _capture_format.format(prefix=self._file_prefix) % self._image_number)
				self._image_number += 1
				shutil.copyfile(filename, newFile)

	def clean_capture_dir(self):
		if not os.path.isdir(self._capture_dir):
			self._logger.warn("Cannot clean capture directory, it is unset")
			return
		delete_unrendered_timelapse(self._file_prefix)



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
		# we always copy the final image for the whole post roll
		# for z based timelapses
		self._copying_postroll()
		Timelapse.process_post_roll(self)

	def _on_z_change(self, event, payload):
		if self._retraction_zhop != 0 and payload["old"] is not None and payload["new"] is not None:
			# check if height difference equals z-hop or is negative, if so don't take a picture
			diff = round(payload["new"] - payload["old"], 3)
			zhop = round(self._retraction_zhop, 3)
			if diff == zhop or diff <= 0:
				return

		self.capture_image()


class TimedTimelapse(Timelapse):
	def __init__(self, post_roll=0, interval=1, fps=25, capture_post_roll=True):
		Timelapse.__init__(self, post_roll=post_roll, fps=fps)
		self._interval = interval
		if self._interval < 1:
			self._interval = 1 # force minimum interval of 1s
		self._capture_post_roll = capture_post_roll
		self._postroll_captures = 0
		self._timer = None
		self._logger.debug("TimedTimelapse initialized")

	@property
	def interval(self):
		return self._interval

	@property
	def capture_post_roll(self):
		return self._capture_post_roll

	def config_data(self):
		return {
			"type": "timed",
			"options": {
				"interval": self._interval,
				"capture_post_roll": self._capture_post_roll
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
		if self._capture_post_roll:
			self._postroll_captures = self._post_roll * self._fps
		else:
			self._postroll_captures = 0
		Timelapse.on_print_done(self, event, payload)

	def calculate_post_roll(self):
		if self._capture_post_roll:
			return self._post_roll * self._fps * self._interval
		else:
			return Timelapse.calculate_post_roll(self)

	def process_post_roll(self):
		if self._capture_post_roll:
			return

		# we only use the final image as post roll if we
		# are not supposed to capture it
		self._copying_postroll()
		self.post_roll_finished()

	def post_roll_finished(self):
		Timelapse.post_roll_finished(self)
		self._timer = None

	def _timer_active(self):
		return self._in_timelapse or self._postroll_captures > 0

	def _timer_task(self):
		self.capture_image()
		if self._postroll_captures > 0:
			self._postroll_captures -= 1

	def _on_timer_finished(self):
		if self._capture_post_roll:
			self.post_roll_finished()


class TimelapseRenderJob(object):

	render_job_lock = threading.RLock()

	def __init__(self, capture_dir, output_dir, prefix, postfix=None, capture_glob="{prefix}-*.jpg",
	             capture_format="{prefix}-%d.jpg", output_format="{prefix}{postfix}.mpg", fps=25, threads=1,
	             on_start=None, on_success=None, on_fail=None, on_always=None):
		self._capture_dir = capture_dir
		self._output_dir = output_dir
		self._prefix = prefix
		self._postfix = postfix
		self._capture_glob = capture_glob
		self._capture_format = capture_format
		self._output_format = output_format
		self._fps = fps
		self._threads = threads
		self._on_start = on_start
		self._on_success = on_success
		self._on_fail = on_fail
		self._on_always = on_always

		self._thread = None
		self._logger = logging.getLogger(__name__)

	def process(self):
		"""Processes the job."""

		self._thread = threading.Thread(target=self._render,
		                                name="TimelapseRenderJob_{prefix}_{postfix}".format(prefix=self._prefix,
		                                                                                    postfix=self._postfix))
		self._thread.daemon = True
		self._thread.start()

	def _render(self):
		"""Rendering runnable."""

		ffmpeg = settings().get(["webcam", "ffmpeg"])
		bitrate = settings().get(["webcam", "bitrate"])
		if ffmpeg is None or bitrate is None:
			self._logger.warn("Cannot create movie, path to ffmpeg or desired bitrate is unset")
			return

		input = os.path.join(self._capture_dir,
		                     self._capture_format.format(prefix=self._prefix,
		                                                 postfix=self._postfix if self._postfix is not None else ""))
		output = os.path.join(self._output_dir,
		                      self._output_format.format(prefix=self._prefix,
		                                                 postfix=self._postfix if self._postfix is not None else ""))

		for i in range(4):
			if os.path.exists(input % i):
				break
		else:
			self._logger.warn("Cannot create a movie, no frames captured")
			self._notify_callback("fail", output, returncode=0, stdout="", stderr="", reason="no_frames")
			return

		hflip = settings().getBoolean(["webcam", "flipH"])
		vflip = settings().getBoolean(["webcam", "flipV"])
		rotate = settings().getBoolean(["webcam", "rotate90"])

		watermark = None
		if settings().getBoolean(["webcam", "watermark"]):
			watermark = os.path.join(os.path.dirname(__file__), "static", "img", "watermark.png")
			if sys.platform == "win32":
				# Because ffmpeg hiccups on windows' drive letters and backslashes we have to give the watermark
				# path a special treatment. Yeah, I couldn't believe it either...
				watermark = watermark.replace("\\", "/").replace(":", "\\\\:")

		# prepare ffmpeg command
		command_str = self._create_ffmpeg_command_string(ffmpeg, self._fps, bitrate, self._threads, input, output,
		                                                 hflip=hflip, vflip=vflip, rotate=rotate, watermark=watermark)
		self._logger.debug("Executing command: {}".format(command_str))

		with self.render_job_lock:
			try:
				self._notify_callback("start", output)
				p = sarge.run(command_str, stdout=sarge.Capture(), stderr=sarge.Capture())
				if p.returncode == 0:
					self._notify_callback("success", output)
				else:
					returncode = p.returncode
					stdout_text = p.stdout.text
					stderr_text = p.stderr.text
					self._logger.warn("Could not render movie, got return code %r: %s" % (returncode, stderr_text))
					self._notify_callback("fail", output, returncode=returncode, stdout=stdout_text, stderr=stderr_text, reason="returncode")
			except:
				self._logger.exception("Could not render movie due to unknown error")
				self._notify_callback("fail", output, reason="unknown")
			finally:
				self._notify_callback("always", output)

	@classmethod
	def _create_ffmpeg_command_string(cls, ffmpeg, fps, bitrate, threads, input, output, hflip=False, vflip=False,
	                                  rotate=False, watermark=None):
		"""
		Create ffmpeg command string based on input parameters.

		Examples:

		    >>> TimelapseRenderJob._create_ffmpeg_command_string("/path/to/ffmpeg", 25, "10000k", 1, "/path/to/input/files_%d.jpg", "/path/to/output.mpg")
		    '/path/to/ffmpeg -framerate 25 -loglevel error -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -pix_fmt yuv420p -r 25 -y -b 10000k -f vob "/path/to/output.mpg"'
		    >>> TimelapseRenderJob._create_ffmpeg_command_string("/path/to/ffmpeg", 25, "10000k", 1, "/path/to/input/files_%d.jpg", "/path/to/output.mpg", hflip=True)
		    '/path/to/ffmpeg -framerate 25 -loglevel error -i "/path/to/input/files_%d.jpg" -vcodec mpeg2video -threads 1 -pix_fmt yuv420p -r 25 -y -b 10000k -f vob -vf \\'[in] hflip [out]\\' "/path/to/output.mpg"'

		Arguments:
		    ffmpeg (str): Path to ffmpeg
		    fps (int): Frames per second for output
		    bitrate (str): Bitrate of output
		    threads (int): Number of threads to use for rendering
		    input (str): Absolute path to input files including file mask
		    output (str): Absolute path to output file
		    hflip (bool): Perform horizontal flip on input material.
		    vflip (bool): Perform vertical flip on input material.
		    rotate (bool): Perform 90° CCW rotation on input material.
		    watermark (str): Path to watermark to apply to lower left corner.

		Returns:
		    (str): Prepared command string to render `input` to `output` using ffmpeg.
		"""

		logger = logging.getLogger(__name__)

		command = [
			ffmpeg, '-framerate', str(fps), '-loglevel', 'error', '-i', '"{}"'.format(input), '-vcodec', 'mpeg2video',
			'-threads', str(threads), '-pix_fmt', 'yuv420p', '-r', "25", '-y', '-b', str(bitrate),
			'-f', 'vob']

		filter_string = cls._create_filter_string(hflip=hflip,
		                                          vflip=vflip,
		                                          rotate=rotate,
		                                          watermark=watermark)

		if filter_string is not None:
			logger.debug("Applying videofilter chain: {}".format(filter_string))
			command.extend(["-vf", sarge.shell_quote(filter_string)])

		# finalize command with output file
		logger.debug("Rendering movie to {}".format(output))
		command.append('"{}"'.format(output))

		return " ".join(command)

	@classmethod
	def _create_filter_string(cls, hflip=False, vflip=False, rotate=False, watermark=None):
		"""
		Creates an ffmpeg filter string based on input parameters.

		Examples:

		    >>> TimelapseRenderJob._create_filter_string()
		    >>> TimelapseRenderJob._create_filter_string(hflip=True)
		    '[in] hflip [out]'
		    >>> TimelapseRenderJob._create_filter_string(vflip=True)
		    '[in] vflip [out]'
		    >>> TimelapseRenderJob._create_filter_string(rotate=True)
		    '[in] transpose=2 [out]'
		    >>> TimelapseRenderJob._create_filter_string(vflip=True, rotate=True)
		    '[in] vflip,transpose=2 [out]'
		    >>> TimelapseRenderJob._create_filter_string(vflip=True, hflip=True, rotate=True)
		    '[in] hflip,vflip,transpose=2 [out]'
		    >>> TimelapseRenderJob._create_filter_string(watermark="/path/to/watermark.png")
		    'movie=/path/to/watermark.png [wm]; [in][wm] overlay=10:main_h-overlay_h-10 [out]'
		    >>> TimelapseRenderJob._create_filter_string(hflip=True, watermark="/path/to/watermark.png")
		    '[in] hflip [postprocessed]; movie=/path/to/watermark.png [wm]; [postprocessed][wm] overlay=10:main_h-overlay_h-10 [out]'

		Arguments:
		    hflip (bool): Perform horizontal flip on input material.
		    vflip (bool): Perform vertical flip on input material.
		    rotate (bool): Perform 90° CCW rotation on input material.
		    watermark (str): Path to watermark to apply to lower left corner.

		Returns:
		    (str or None): filter string or None if no filters are required
		"""
		filters = []

		# flip video if configured
		if hflip:
			filters.append('hflip')
		if vflip:
			filters.append('vflip')
		if rotate:
			filters.append('transpose=2')

		# add watermark if configured
		watermark_filter = None
		if watermark is not None:
			watermark_filter = "movie={} [wm]; [{{input_name}}][wm] overlay=10:main_h-overlay_h-10".format(watermark)

		filter_string = None
		if len(filters) > 0:
			if watermark_filter is not None:
				filter_string = "[in] {} [postprocessed]; {} [out]".format(",".join(filters),
				                                                           watermark_filter.format(input_name="postprocessed"))
			else:
				filter_string = "[in] {} [out]".format(",".join(filters))
		elif watermark_filter is not None:
			filter_string = watermark_filter.format(input_name="in") + " [out]"

		return filter_string

	def _notify_callback(self, callback, *args, **kwargs):
		"""Notifies registered callbacks of type `callback`."""
		name = "_on_{}".format(callback)
		method = getattr(self, name, None)
		if method is not None and callable(method):
			method(*args, **kwargs)
