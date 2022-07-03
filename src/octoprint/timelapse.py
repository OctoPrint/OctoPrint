__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

import collections
import datetime
import fnmatch
import glob
import logging
import os
import queue
import re
import shutil
import sys
import threading
import time

import requests
import sarge

import octoprint.plugin
import octoprint.util as util
from octoprint.events import Events, eventManager
from octoprint.plugin import plugin_manager
from octoprint.settings import settings
from octoprint.util import get_fully_qualified_classname as fqcn
from octoprint.util import sv
from octoprint.util.commandline import CommandlineCaller

# currently configured timelapse
current = None

# currently active render job, if any
current_render_job = None

# filename formats
_capture_format = "{prefix}-%d.jpg"
_capture_glob = "{prefix}-*.jpg"
_output_format = "{prefix}{postfix}.{extension}"

# thumbnails
_thumbnail_extension = ".thumb.jpg"
_thumbnail_format = "{}.thumb.jpg"


# ffmpeg progress regexes
_ffmpeg_duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}")
_ffmpeg_current_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")

# old capture format, needed to delete old left-overs from
# versions <1.2.9
_old_capture_format_re = re.compile(r"^tmp_\d{5}.jpg$")

# valid timelapses
_valid_timelapse_types = ["off", "timed", "zchange"]

# callbacks for timelapse config updates
_update_callbacks = []

# lock for timelapse cleanup, must be re-entrant
_cleanup_lock = threading.RLock()

# lock for timelapse job
_job_lock = threading.RLock()

# cached valid timelapse extensions
_extensions = None


def create_thumbnail_path(movie_path):
    return _thumbnail_format.format(movie_path)


def valid_timelapse(path):
    global _extensions

    if _extensions is None:
        # create list of extensions
        extensions = ["mpg", "mpeg", "mp4", "m4v", "mkv"]

        hooks = plugin_manager().get_hooks("octoprint.timelapse.extensions")
        for name, hook in hooks.items():
            try:
                result = hook()
                if result is None or not isinstance(result, list):
                    continue
                extensions += result
            except Exception:
                logging.getLogger(__name__).exception(
                    "Exception while retrieving additional timelapse "
                    "extensions from hook {name}".format(name=name),
                    extra={"plugin": name},
                )

        _extensions = list(set(extensions))

    return util.is_allowed_file(path, _extensions)


def valid_timelapse_thumbnail(path):
    global _thumbnail_extensions
    # Thumbnail path is valid if it ends with thumbnail extension and path without extension is valid timelpase
    if path.endswith(_thumbnail_extension):
        return valid_timelapse(path[: -len(_thumbnail_extension)])
    else:
        return False


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
    return os.stat(settings().getBaseFolder("timelapse", check_writable=False)).st_mtime


def last_modified_unrendered():
    return os.stat(
        settings().getBaseFolder("timelapse_tmp", check_writable=False)
    ).st_mtime


def get_finished_timelapses():
    files = []
    basedir = settings().getBaseFolder("timelapse", check_writable=False)
    for entry in os.scandir(basedir):
        if util.is_hidden_path(entry.path) or not valid_timelapse(entry.path):
            continue

        thumb = create_thumbnail_path(entry.path)
        if os.path.isfile(thumb) is True:
            thumb = os.path.basename(thumb)
        else:
            thumb = None

        files.append(
            {
                "name": entry.name,
                "size": util.get_formatted_size(entry.stat().st_size),
                "bytes": entry.stat().st_size,
                "thumbnail": thumb,
                "timestamp": entry.stat().st_mtime,
                "date": util.get_formatted_datetime(
                    datetime.datetime.fromtimestamp(entry.stat().st_mtime)
                ),
            }
        )
    return files


def get_unrendered_timelapses():
    global _job_lock
    global current

    delete_old_unrendered_timelapses()

    basedir = settings().getBaseFolder("timelapse_tmp", check_writable=False)
    jobs = collections.defaultdict(
        lambda: {"count": 0, "size": None, "bytes": 0, "date": None, "timestamp": None}
    )

    for entry in os.scandir(basedir):
        if not fnmatch.fnmatch(entry.name, "*.jpg"):
            continue

        prefix = _extract_prefix(entry.name)
        if prefix is None:
            continue

        jobs[prefix]["count"] += 1
        jobs[prefix]["bytes"] += entry.stat().st_size
        if (
            jobs[prefix]["timestamp"] is None
            or entry.stat().st_mtime < jobs[prefix]["timestamp"]
        ):
            jobs[prefix]["timestamp"] = entry.stat().st_mtime

    with _job_lock:
        global current_render_job

        def finalize_fields(prefix, job):
            currently_recording = current is not None and current.prefix == prefix
            currently_rendering = (
                current_render_job is not None and current_render_job["prefix"] == prefix
            )

            job["size"] = util.get_formatted_size(job["bytes"])
            job["date"] = util.get_formatted_datetime(
                datetime.datetime.fromtimestamp(job["timestamp"])
            )
            job["recording"] = currently_recording
            job["rendering"] = currently_rendering
            job["processing"] = currently_recording or currently_rendering
            del job["timestamp"]

            return job

        return sorted(
            (
                util.dict_merge({"name": key}, finalize_fields(key, value))
                for key, value in jobs.items()
            ),
            key=lambda x: sv(x["name"]),
        )


def delete_unrendered_timelapse(name):
    global _cleanup_lock

    pattern = f"{glob.escape(name)}*.jpg"

    basedir = settings().getBaseFolder("timelapse_tmp")
    with _cleanup_lock:
        for entry in os.scandir(basedir):
            try:
                if fnmatch.fnmatch(entry.name, pattern):
                    os.remove(entry.path)
            except Exception:
                if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
                    logging.getLogger(__name__).exception(
                        f"Error while processing file {entry.name} during cleanup"
                    )


def render_unrendered_timelapse(name, gcode=None, postfix=None, fps=None):
    capture_dir = settings().getBaseFolder("timelapse_tmp")
    output_dir = settings().getBaseFolder("timelapse")

    if fps is None:
        fps = settings().getInt(["webcam", "timelapse", "fps"])
    threads = settings().get(["webcam", "ffmpegThreads"])
    videocodec = settings().get(["webcam", "ffmpegVideoCodec"])

    job = TimelapseRenderJob(
        capture_dir,
        output_dir,
        name,
        postfix=postfix,
        fps=fps,
        threads=threads,
        videocodec=videocodec,
        on_start=_create_render_start_handler(name, gcode=gcode),
        on_success=_create_render_success_handler(name, gcode=gcode),
        on_fail=_create_render_fail_handler(name, gcode=gcode),
        on_always=_create_render_always_handler(name, gcode=gcode),
    )
    job.process()


def delete_old_unrendered_timelapses():
    global _cleanup_lock

    basedir = settings().getBaseFolder("timelapse_tmp")
    clean_after_days = settings().getInt(["webcam", "cleanTmpAfterDays"])
    cutoff = time.time() - clean_after_days * 24 * 60 * 60

    prefixes_to_clean = []

    with _cleanup_lock:
        for entry in os.scandir(basedir):
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

                # delete if both creation and modification time are older than the cutoff
                if max(entry.stat().st_ctime, entry.stat().st_mtime) < cutoff:
                    prefixes_to_clean.append(prefix)
            except Exception:
                if logging.getLogger(__name__).isEnabledFor(logging.DEBUG):
                    logging.getLogger(__name__).exception(
                        f"Error while processing file {entry.name} during cleanup"
                    )

        for prefix in prefixes_to_clean:
            delete_unrendered_timelapse(prefix)
            logging.getLogger(__name__).info(f"Deleted old unrendered timelapse {prefix}")


def _create_render_start_handler(name, gcode=None):
    def f(movie):
        global _job_lock

        with _job_lock:
            global current_render_job
            payload = {
                "gcode": gcode if gcode is not None else "unknown",
                "movie": movie,
                "movie_basename": os.path.basename(movie),
                "movie_prefix": name,
            }
            current_render_job = {"prefix": name}
            current_render_job.update(payload)
        eventManager().fire(Events.MOVIE_RENDERING, payload)

    return f


def _create_render_success_handler(name, gcode=None):
    def f(movie):
        delete_unrendered_timelapse(name)
        payload = {
            "gcode": gcode if gcode is not None else "unknown",
            "movie": movie,
            "movie_basename": os.path.basename(movie),
            "movie_prefix": name,
        }
        eventManager().fire(Events.MOVIE_DONE, payload)

    return f


def _create_render_fail_handler(name, gcode=None):
    def f(
        movie,
        returncode=255,
        stdout="Unknown error",
        stderr="Unknown error",
        reason="unknown",
    ):
        payload = {
            "gcode": gcode if gcode is not None else "unknown",
            "movie": movie,
            "movie_basename": os.path.basename(movie),
            "movie_prefix": name,
            "returncode": returncode,
            "out": stdout,
            "error": stderr,
            "reason": reason,
        }
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
    if callback not in _update_callbacks:
        _update_callbacks.append(callback)


def unregister_callback(callback):
    try:
        _update_callbacks.remove(callback)
    except ValueError:
        # not registered
        pass


def notify_callbacks(timelapse):
    if timelapse is None:
        config = None
    else:
        config = timelapse.config_data()

    for callback in _update_callbacks:
        notify_callback(callback, config)


def notify_callback(callback, config=None, timelapse=None):
    if config is None and timelapse is not None:
        config = timelapse.config_data()

    try:
        callback.sendTimelapseConfig(config)
    except Exception:
        logging.getLogger(__name__).exception(
            "Exception while pushing timelapse configuration",
            extra={"callback": fqcn(callback)},
        )


def configure_timelapse(config=None, persist=False):
    global current

    if config is None:
        config = settings().get(["webcam", "timelapse"], merged=True)

    if current is not None:
        current.unload()

    snapshot_url = settings().get(["webcam", "snapshot"])
    ffmpeg_path = settings().get(["webcam", "ffmpeg"])
    timelapse_enabled = settings().getBoolean(["webcam", "timelapseEnabled"])
    timelapse_precondition = (
        snapshot_url is not None
        and snapshot_url.strip() != ""
        and ffmpeg_path is not None
        and ffmpeg_path.strip() != ""
    )

    type = config["type"]
    if not timelapse_precondition and timelapse_precondition:
        logging.getLogger(__name__).warning(
            "Essential timelapse settings unconfigured (snapshot URL or FFMPEG path) "
            "but timelapse enabled."
        )

    if (
        not timelapse_enabled
        or not timelapse_precondition
        or type is None
        or "off" == type
    ):
        current = None

    else:
        postRoll = 0
        if "postRoll" in config and config["postRoll"] >= 0:
            postRoll = config["postRoll"]

        fps = 25
        if "fps" in config and config["fps"] > 0:
            fps = config["fps"]

        if "zchange" == type:
            retractionZHop = 0
            if (
                "options" in config
                and "retractionZHop" in config["options"]
                and config["options"]["retractionZHop"] >= 0
            ):
                retractionZHop = config["options"]["retractionZHop"]

            minDelay = 5
            if (
                "options" in config
                and "minDelay" in config["options"]
                and config["options"]["minDelay"] > 0
            ):
                minDelay = config["options"]["minDelay"]

            current = ZTimelapse(
                post_roll=postRoll,
                retraction_zhop=retractionZHop,
                min_delay=minDelay,
                fps=fps,
            )

        elif "timed" == type:
            interval = 10
            if (
                "options" in config
                and "interval" in config["options"]
                and config["options"]["interval"] > 0
            ):
                interval = config["options"]["interval"]

            current = TimedTimelapse(post_roll=postRoll, interval=interval, fps=fps)

    notify_callbacks(current)

    if persist:
        settings().set(["webcam", "timelapse"], config)
        settings().save()


class Timelapse:
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
        self._on_post_roll_done = None

        self._capture_dir = settings().getBaseFolder("timelapse_tmp")
        self._movie_dir = settings().getBaseFolder("timelapse")
        self._snapshot_url = settings().get(["webcam", "snapshot"])
        self._snapshot_timeout = settings().getInt(["webcam", "snapshotTimeout"])
        self._snapshot_validate_ssl = settings().getBoolean(
            ["webcam", "snapshotSslValidation"]
        )

        self._fps = fps

        self._pluginManager = octoprint.plugin.plugin_manager()
        self._pre_capture_hooks = self._pluginManager.get_hooks(
            "octoprint.timelapse.capture.pre"
        )
        self._post_capture_hooks = self._pluginManager.get_hooks(
            "octoprint.timelapse.capture.post"
        )

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
        self.start_timelapse(payload["name"])

    def on_print_done(self, event, payload):
        """
        Override this to perform additional actions upon the stop of a print job.
        """
        self.stop_timelapse(success=(event == Events.PRINT_DONE))

    def on_print_resumed(self, event, payload):
        """
        Override this to perform additional actions upon the pausing of a print job.
        """
        if not self._in_timelapse:
            self.start_timelapse(payload["name"])

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

    def start_timelapse(self, gcode_file):
        self._logger.debug("Starting timelapse for %s" % gcode_file)

        self._image_number = 0
        self._capture_errors = 0
        self._capture_success = 0
        self._in_timelapse = True
        self._gcode_file = os.path.basename(gcode_file)
        self._file_prefix = "{}_{}".format(
            os.path.splitext(self._gcode_file)[0].replace("%", "%%"),
            time.strftime("%Y%m%d%H%M%S"),
        )

    def stop_timelapse(self, do_create_movie=True, success=True):
        self._logger.debug("Stopping timelapse")

        self._in_timelapse = False

        def reset_image_number():
            self._image_number = None

        def create_movie():
            render_unrendered_timelapse(
                self._file_prefix,
                gcode=self._gcode_file,
                postfix=None if success else "-fail",
                fps=self._fps,
            )

        def reset_and_create():
            reset_image_number()
            create_movie()

        def wait_for_captures(callback):
            self._capture_queue.put(
                {"type": self.__class__.QUEUE_ENTRY_TYPE_CALLBACK, "callback": callback}
            )

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
                    _create_render_fail_handler(
                        self._file_prefix, gcode=self._gcode_file
                    )("n/a", returncode=0, stdout="", stderr="", reason="no_frames")

                # in any case, don't continue
                return

            # check if we have post roll configured
            if self._post_roll > 0:
                # capture post roll, wait for THAT to finish, THEN render
                eventManager().fire(
                    Events.POSTROLL_START,
                    {
                        "postroll_duration": self.calculate_post_roll(),
                        "postroll_length": self.post_roll,
                        "postroll_fps": self.fps,
                    },
                )
                if do_create_movie:
                    self._on_post_roll_done = create_wait_for_captures(reset_and_create)
                else:
                    self._on_post_roll_done = reset_image_number
                self.process_post_roll()
            else:
                # no post roll? perfect, render
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
            self._logger.warning("Cannot capture image, capture directory is unset")
            return

        with self._capture_mutex:
            if self._image_number is None:
                self._logger.warning("Cannot capture image, image number is unset")
                return

            filename = os.path.join(
                self._capture_dir,
                _capture_format.format(prefix=self._file_prefix) % self._image_number,
            )
            self._image_number += 1

        self._logger.debug(f"Capturing image to {filename}")
        entry = {
            "type": self.__class__.QUEUE_ENTRY_TYPE_CAPTURE,
            "filename": filename,
            "onerror": self._on_capture_error,
        }
        self._capture_queue.put(entry)
        return filename

    def _on_capture_error(self):
        with self._capture_mutex:
            if self._image_number is not None and self._image_number > 0:
                self._image_number -= 1

    def _capture_queue_worker(self):
        while self._capture_queue_active:
            entry = self._capture_queue.get(block=True)

            if (
                entry["type"] == self.__class__.QUEUE_ENTRY_TYPE_CAPTURE
                and "filename" in entry
            ):
                filename = entry["filename"]
                onerror = entry.pop("onerror", None)
                self._perform_capture(filename, onerror=onerror)

            elif (
                entry["type"] == self.__class__.QUEUE_ENTRY_TYPE_CALLBACK
                and "callback" in entry
            ):
                args = entry.pop("args", [])
                kwargs = entry.pop("kwargs", {})
                entry["callback"](*args, **kwargs)

    def _perform_capture(self, filename, onerror=None):
        # pre-capture hook
        for name, hook in self._pre_capture_hooks.items():
            try:
                hook(filename)
            except Exception:
                self._logger.exception(f"Error while processing hook {name}.")

        eventManager().fire(Events.CAPTURE_START, {"file": filename})
        try:
            self._logger.debug(f"Going to capture {filename} from {self._snapshot_url}")
            r = requests.get(
                self._snapshot_url,
                stream=True,
                timeout=self._snapshot_timeout,
                verify=self._snapshot_validate_ssl,
            )
            r.raise_for_status()

            with open(filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()

            self._logger.debug(f"Image {filename} captured from {self._snapshot_url}")
        except Exception as e:
            self._logger.exception(
                f"Could not capture image {filename} from {self._snapshot_url}"
            )
            self._capture_errors += 1
            err = e
        else:
            self._capture_success += 1
            err = None

        # post-capture hook
        for name, hook in self._post_capture_hooks.items():
            try:
                hook(filename, err is None)
            except Exception:
                self._logger.exception(f"Error while processing hook {name}.")

        # handle events and onerror call
        if err is None:
            eventManager().fire(Events.CAPTURE_DONE, {"file": filename})
            return True
        else:
            if callable(onerror):
                onerror()
            eventManager().fire(
                Events.CAPTURE_FAILED,
                {"file": filename, "error": str(err), "url": self._snapshot_url},
            )
            return False

    def _copying_postroll(self):
        with self._capture_mutex:
            filename = os.path.join(
                self._capture_dir,
                _capture_format.format(prefix=self._file_prefix) % self._image_number,
            )
            self._image_number += 1

        if self._perform_capture(filename):
            for _ in range(self._post_roll * self._fps):
                newFile = os.path.join(
                    self._capture_dir,
                    _capture_format.format(prefix=self._file_prefix) % self._image_number,
                )
                self._image_number += 1
                shutil.copyfile(filename, newFile)

    def clean_capture_dir(self):
        if not os.path.isdir(self._capture_dir):
            self._logger.warning("Cannot clean capture directory, it is unset")
            return
        delete_unrendered_timelapse(self._file_prefix)


class ZTimelapse(Timelapse):
    def __init__(self, retraction_zhop=0, min_delay=5.0, post_roll=0, fps=25):
        Timelapse.__init__(self, post_roll=post_roll, fps=fps)

        if min_delay < 0:
            min_delay = 0

        self._retraction_zhop = retraction_zhop
        self._min_delay = min_delay
        self._last_snapshot = None
        self._logger.debug("ZTimelapse initialized")

    @property
    def retraction_zhop(self):
        return self._retraction_zhop

    @property
    def min_delay(self):
        return self._min_delay

    def event_subscriptions(self):
        return [(Events.Z_CHANGE, self._on_z_change)]

    def config_data(self):
        return {"type": "zchange", "options": {"retractionZHop": self._retraction_zhop}}

    def process_post_roll(self):
        # we always copy the final image for the whole post roll
        # for z based timelapses
        self._copying_postroll()
        Timelapse.process_post_roll(self)

    def _on_z_change(self, event, payload):
        # check if height difference equals z-hop, if so don't take a picture
        if (
            self._retraction_zhop != 0
            and payload["old"] is not None
            and payload["new"] is not None
        ):
            diff = round(abs(payload["new"] - payload["old"]), 3)
            zhop = round(self._retraction_zhop, 3)
            if diff == zhop:
                return

        # check if last picture has been less than min_delay ago, if so don't take a picture (anti vase mode...)
        now = time.monotonic()
        if (
            self._min_delay
            and self._last_snapshot
            and self._last_snapshot + self._min_delay > now
        ):
            self._logger.debug("Rate limited z-change, not taking a snapshot")
            return

        self.capture_image()
        self._last_snapshot = now


class TimedTimelapse(Timelapse):
    def __init__(self, interval=1, post_roll=0, fps=25):
        Timelapse.__init__(self, post_roll=post_roll, fps=fps)
        self._interval = interval
        if self._interval < 1:
            self._interval = 1  # force minimum interval of 1s
        self._timer = None
        self._logger.debug("TimedTimelapse initialized")

    @property
    def interval(self):
        return self._interval

    def config_data(self):
        return {"type": "timed", "options": {"interval": self._interval}}

    def on_print_started(self, event, payload):
        Timelapse.on_print_started(self, event, payload)
        if self._timer is not None:
            return

        self._logger.debug("Starting timer for interval based timelapse")
        from octoprint.util import RepeatedTimer

        self._timer = RepeatedTimer(
            self._interval,
            self._timer_task,
            run_first=True,
            condition=self._timer_active,
            on_finish=self._on_timer_finished,
        )
        self._timer.start()

    def process_post_roll(self):
        # we only use the final image as post roll
        self._copying_postroll()
        self.post_roll_finished()

    def _timer_active(self):
        return self._in_timelapse

    def _timer_task(self):
        self.capture_image()

    def _on_timer_finished(self):
        # timer is done, delete it
        self._timer = None


class TimelapseRenderJob:

    render_job_lock = threading.RLock()

    def __init__(
        self,
        capture_dir,
        output_dir,
        prefix,
        postfix=None,
        capture_glob=_capture_glob,
        capture_format=_capture_format,
        output_format=_output_format,
        fps=25,
        threads=1,
        videocodec="mpeg2video",
        on_start=None,
        on_success=None,
        on_fail=None,
        on_always=None,
    ):
        self._capture_dir = capture_dir
        self._output_dir = output_dir
        self._prefix = prefix
        self._postfix = postfix
        self._capture_glob = capture_glob
        self._capture_format = capture_format
        self._output_format = output_format
        self._fps = fps
        self._threads = threads
        self._videocodec = videocodec
        self._on_start = on_start
        self._on_success = on_success
        self._on_fail = on_fail
        self._on_always = on_always

        self._thread = None
        self._logger = logging.getLogger(__name__)

        self._parsed_duration = 0

    def process(self):
        """Processes the job."""

        self._thread = threading.Thread(
            target=self._render,
            name="TimelapseRenderJob_{prefix}_{postfix}".format(
                prefix=self._prefix, postfix=self._postfix
            ),
        )
        self._thread.daemon = True
        self._thread.start()

    def _render(self):
        """Rendering runnable."""

        ffmpeg = settings().get(["webcam", "ffmpeg"])
        commandline = settings().get(["webcam", "ffmpegCommandline"])
        bitrate = settings().get(["webcam", "bitrate"])
        if ffmpeg is None or bitrate is None:
            self._logger.warning(
                "Cannot create movie, path to ffmpeg or desired bitrate is unset"
            )
            return

        if self._videocodec == "mpeg2video":
            extension = "mpg"
        else:
            extension = "mp4"

        input = os.path.join(
            self._capture_dir,
            self._capture_format.format(
                prefix=self._prefix,
                postfix=self._postfix if self._postfix is not None else "",
            ),
        )

        output_name = self._output_format.format(
            prefix=self._prefix,
            postfix=self._postfix if self._postfix is not None else "",
            extension=extension,
        )
        temporary = os.path.join(self._output_dir, f".{output_name}")
        output = os.path.join(self._output_dir, output_name)

        for i in range(4):
            if os.path.exists(input % i):
                break
        else:
            self._logger.warning("Cannot create a movie, no frames captured")
            self._notify_callback(
                "fail", output, returncode=0, stdout="", stderr="", reason="no_frames"
            )
            return

        hflip = settings().getBoolean(["webcam", "flipH"])
        vflip = settings().getBoolean(["webcam", "flipV"])
        rotate = settings().getBoolean(["webcam", "rotate90"])

        watermark = None
        if settings().getBoolean(["webcam", "watermark"]):
            watermark = os.path.join(
                os.path.dirname(__file__), "static", "img", "watermark.png"
            )
            if sys.platform == "win32":
                # Because ffmpeg hiccups on windows' drive letters and backslashes we have to give the watermark
                # path a special treatment. Yeah, I couldn't believe it either...
                watermark = watermark.replace("\\", "/").replace(":", "\\\\:")

        # prepare ffmpeg command
        command_str = self._create_ffmpeg_command_string(
            commandline,
            ffmpeg,
            self._fps,
            bitrate,
            self._threads,
            input,
            temporary,
            self._videocodec,
            hflip=hflip,
            vflip=vflip,
            rotate=rotate,
            watermark=watermark,
        )
        self._logger.debug(f"Executing command: {command_str}")

        with self.render_job_lock:
            try:
                self._notify_callback("start", output)

                self._logger.debug("Parsing ffmpeg output")

                c = CommandlineCaller()
                c.on_log_stderr = self._process_ffmpeg_output
                returncode, stdout_text, stderr_text = c.call(
                    command_str, delimiter=b"\r", buffer_size=512
                )

                self._logger.debug("Done with parsing")

                if returncode == 0:
                    shutil.move(temporary, output)
                    self._try_generate_thumbnail(
                        ffmpeg=ffmpeg,
                        movie_path=output,
                    )
                    self._notify_callback("success", output)
                else:
                    self._logger.warning(
                        "Could not render movie, got return code %r: %s"
                        % (returncode, stderr_text)
                    )
                    self._notify_callback(
                        "fail",
                        output,
                        returncode=returncode,
                        stdout=stdout_text,
                        stderr=stderr_text,
                        reason="returncode",
                    )
            except Exception:
                self._logger.exception("Could not render movie due to unknown error")
                self._notify_callback("fail", output, reason="unknown")
            finally:
                try:
                    if os.path.exists(temporary):
                        os.remove(temporary)
                except Exception:
                    self._logger.warning(
                        f"Could not delete temporary timelapse {temporary}"
                    )
                self._notify_callback("always", output)

    def _process_ffmpeg_output(self, *lines):
        for line in lines:
            # We should be getting the time more often, so try it first
            current_time = _ffmpeg_current_regex.search(line)
            if current_time is not None and self._parsed_duration != 0:
                current_s = self._convert_time(*current_time.groups())
                progress = current_s / self._parsed_duration * 100

                # Update progress bar
                for callback in _update_callbacks:
                    try:
                        callback.sendRenderProgress(progress)
                    except Exception:
                        self._logger.exception("Exception while pushing render progress")

            else:
                duration = _ffmpeg_duration_regex.search(line)
                if duration is not None:
                    self._parsed_duration = self._convert_time(*duration.groups())

    @classmethod
    def _try_generate_thumbnail(cls, ffmpeg, movie_path):
        logger = logging.getLogger(__name__)

        try:
            thumb_path = create_thumbnail_path(movie_path)
            commandline = settings().get(["webcam", "ffmpegThumbnailCommandline"])
            thumb_command_str = cls._create_ffmpeg_command_string(
                commandline=commandline,
                ffmpeg=ffmpeg,
                input=movie_path,
                output=thumb_path,
                fps=None,
                videocodec=None,
                threads=None,
                bitrate=None,
            )
            c = CommandlineCaller()
            returncode, stdout_text, stderr_text = c.call(
                thumb_command_str, delimiter=b"\r", buffer_size=512
            )
            if returncode != 0:
                logger.warning(
                    "Failed to generate optional thumbnail %r: %s"
                    % (returncode, stderr_text)
                )
            return True
        except Exception as ex:
            logger.warning(
                "Failed to generate thumbnail from {} to {} ({})".format(
                    movie_path, thumb_path, ex
                )
            )
            return False

    @staticmethod
    def _convert_time(hours, minutes, seconds):
        return (int(hours) * 60 + int(minutes)) * 60 + int(seconds)

    @classmethod
    def _create_ffmpeg_command_string(
        cls,
        commandline,
        ffmpeg,
        fps,
        bitrate,
        threads,
        input,
        output,
        videocodec,
        hflip=False,
        vflip=False,
        rotate=False,
        watermark=None,
        pixfmt="yuv420p",
    ):
        """
        Create ffmpeg command string based on input parameters.

        Arguments:
            commandline (str): Command line template to use
            ffmpeg (str): Path to ffmpeg
            fps (int): Frames per second for output
            bitrate (str): Bitrate of output
            threads (int): Number of threads to use for rendering
            videocodec (str): Videocodec to be used for encoding
            input (str): Absolute path to input files including file mask
            output (str): Absolute path to output file
            hflip (bool): Perform horizontal flip on input material.
            vflip (bool): Perform vertical flip on input material.
            rotate (bool): Perform 90° CCW rotation on input material.
            watermark (str): Path to watermark to apply to lower left corner.
            pixfmt (str): Pixel format to use for output. Default of yuv420p should usually fit the bill.

        Returns:
            (str): Prepared command string to render `input` to `output` using ffmpeg.
        """

        ### See unit tests in test/timelapse/test_timelapse_renderjob.py

        logger = logging.getLogger(__name__)

        ### Not all players can handle non-mpeg2 in VOB format
        if not videocodec:
            videocodec = "libx264"

        if videocodec == "mpeg2video":
            containerformat = "vob"
        else:
            containerformat = "mp4"

        filter_string = cls._create_filter_string(
            hflip=hflip, vflip=vflip, rotate=rotate, watermark=watermark
        )
        placeholders = {
            "ffmpeg": ffmpeg,
            "fps": str(fps if fps else "25"),
            "input": input,
            "output": output,
            "videocodec": videocodec,
            "threads": str(threads if threads else "1"),
            "bitrate": str(bitrate if bitrate else "10000k"),
            "containerformat": containerformat,
            "filters": ("-vf " + sarge.shell_quote(filter_string))
            if filter_string
            else "",
        }

        logger.debug(f"Rendering movie to {output}")
        return commandline.format(**placeholders)

    @classmethod
    def _create_filter_string(
        cls, hflip=False, vflip=False, rotate=False, watermark=None, pixfmt="yuv420p"
    ):
        """
        Creates an ffmpeg filter string based on input parameters.

        Arguments:
            hflip (bool): Perform horizontal flip on input material.
            vflip (bool): Perform vertical flip on input material.
            rotate (bool): Perform 90° CCW rotation on input material.
            watermark (str): Path to watermark to apply to lower left corner.
            pixfmt (str): Pixel format to use, defaults to "yuv420p" which should usually fit the bill

        Returns:
            (str or None): filter string or None if no filters are required
        """

        ### See unit tests in test/timelapse/test_timelapse_renderjob.py

        # apply pixel format
        filters = [f"format={pixfmt}"]

        # flip video if configured
        if hflip:
            filters.append("hflip")
        if vflip:
            filters.append("vflip")
        if rotate:
            filters.append("transpose=2")

        # add watermark if configured
        watermark_filter = None
        if watermark is not None:
            watermark_filter = "movie={} [wm]; [{{input_name}}][wm] overlay=10:main_h-overlay_h-10".format(
                watermark
            )

        filter_string = None
        if len(filters) > 0:
            if watermark_filter is not None:
                filter_string = "[in] {} [postprocessed]; {} [out]".format(
                    ",".join(filters), watermark_filter.format(input_name="postprocessed")
                )
            else:
                filter_string = "[in] {} [out]".format(",".join(filters))
        elif watermark_filter is not None:
            filter_string = watermark_filter.format(input_name="in") + " [out]"

        return filter_string

    def _notify_callback(self, callback, *args, **kwargs):
        """Notifies registered callbacks of type `callback`."""
        name = f"_on_{callback}"
        method = getattr(self, name, None)
        if method is not None and callable(method):
            method(*args, **kwargs)
