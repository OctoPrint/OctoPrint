# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import time
import copy

from octoprint.comm.protocol import ProtocolListener, FileAwareProtocolListener, ProtocolState, FileManagementProtocolMixin

from octoprint.util.listener import ListenerAware

from abc import ABCMeta, abstractmethod, abstractproperty

from octoprint.util import monotonic_time

from future.utils import with_metaclass


class LastResult(object):
	def __init__(self):
		self.elapsed = None
		self.clean_elapsed = None
		self.progress = None
		self.pos = None
		self.success = None

		self.available = False


class Printjob(with_metaclass(ABCMeta, ProtocolListener, ListenerAware)):

	parallel = False
	"""Job runs parallel to regular communication."""

	exclusive = False
	"""Job has exclusive claim to communication channel."""

	def __init__(self, name=None, user=None, event_data=None):
		if event_data is None:
			event_data = dict()

		super(Printjob, self).__init__()
		self._logger = logging.getLogger(__name__)
		self._start = None
		self._protocol = None
		self._printer_profile = None
		self._name = name
		self._user = user
		self._event_data = event_data

		self._lost_time = 0
		self._last_result = LastResult()

	@property
	def name(self):
		return self._name

	@property
	def user(self):
		return self._user

	@property
	def size(self):
		return None

	@property
	def pos(self):
		return None

	@property
	def elapsed(self):
		return monotonic_time() - self._start if self._start is not None else None

	@property
	def clean_elapsed(self):
		elapsed = self.elapsed
		if elapsed is None:
			return None
		return elapsed - self._lost_time

	@property
	def last_result(self):
		return self._last_result

	@property
	def progress(self):
		size = self.size
		pos = self.pos
		if pos is None or size is None or size == 0:
			return None

		return float(pos) / float(size)

	@property
	def active(self):
		return self._start is not None

	def add_to_lost_time(self, value):
		self._lost_time += value

	def can_process(self, protocol):
		return False

	def process(self, protocol, position=0, user=None, tags=None, **kwargs):
		self._last_result = LastResult()
		self._start = monotonic_time()
		self._user = user
		self._protocol = protocol
		self._protocol.register_listener(self)

	def pause(self, user=None, tags=None, **kwargs):
		self.process_job_paused(user=user, tags=tags, **kwargs)

	def resume(self, user=None, tags=None, **kwargs):
		self.process_job_resumed(user=user, tags=tags, **kwargs)

	def cancel(self, error=False, user=None, tags=None, **kwargs):
		if error:
			self.process_job_failed(**kwargs)
		else:
			self.process_job_cancelled(user=user, tags=tags, **kwargs)
		self._protocol.unregister_listener(self)
		self._protocol = None

	def get_next(self):
		return None

	def can_get_content(self):
		return False

	def get_content_generator(self):
		return None

	def event_payload(self, incl_last=False):
		payload = copy.deepcopy(self._event_data)

		payload["owner"] = self._user
		elapsed = self.elapsed
		if elapsed is None and incl_last and self.last_result.available:
			elapsed = self.last_result.elapsed
		if elapsed is not None:
			payload["time"] = elapsed

		return payload

	def process_job_started(self, user=None, tags=None, **kwargs):
		self.notify_listeners("on_job_started", self, user=user, tags=tags, **kwargs)

	def process_job_done(self, user=None, tags=None, **kwargs):
		self.notify_listeners("on_job_done", self, user=user, tags=tags, **kwargs)
		self.report_stats()
		self.reset_job()

	def process_job_failed(self, **kwargs):
		self.notify_listeners("on_job_failed", self, **kwargs)
		self.report_stats()
		self.reset_job(success=False)

	def process_job_cancelled(self, user=None, tags=None, **kwargs):
		self.notify_listeners("on_job_cancelled", self, user=user, tags=tags, **kwargs)
		self.report_stats()
		self.reset_job(success=False)

	def process_job_paused(self, user=None, tags=None, **kwargs):
		self.notify_listeners("on_job_paused", self, user=user, tags=tags, **kwargs)

	def process_job_resumed(self, user=None, tags=None, **kwargs):
		self.notify_listeners("on_job_resumed", self, user=user, tags=tags, **kwargs)

	def process_job_progress(self):
		self.notify_listeners("on_job_progress", self)

	def report_stats(self):
		elapsed = self.elapsed
		if elapsed:
			self._logger.info("Job processed in {}s".format(elapsed))

	def reset_job(self, success=True):
		self._last_result.progress = 1.0 if success else self.progress
		self._last_result.pos = self.size if success else self.pos
		self._last_result.elapsed = self.elapsed
		self._last_result.clean_elapsed = self.clean_elapsed
		self._last_result.success = success
		self._last_result.available = True

		self._start = None
		self._lost_time = 0

	def on_protocol_state(self, protocol, old_state, new_state, *args, **kwargs):
		if new_state in (ProtocolState.DISCONNECTED, ProtocolState.DISCONNECTED_WITH_ERROR) and self.active:
			self.cancel(error=True)


class StoragePrintjob(Printjob):
	def __init__(self, storage, path_in_storage, *args, **kwargs):
		Printjob.__init__(self, *args, **kwargs)
		self._storage = storage
		self._path_in_storage = path_in_storage

	@property
	def storage(self):
		return self._storage

	@property
	def path_in_storage(self):
		return self._path_in_storage

	def event_payload(self, incl_last=False):
		payload = Printjob.event_payload(self, incl_last=incl_last)
		payload["name"] = self.name
		payload["path"] = self.path_in_storage
		payload["origin"] = self.storage
		return payload


class LocalFilePrintjob(StoragePrintjob):

	def __init__(self, path, *args, **kwargs):
		encoding = kwargs.pop("encoding", "utf-8")

		StoragePrintjob.__init__(self, *args, **kwargs)

		if path is None or not os.path.exists(path):
			raise ValueError("path must be set to a local file path")

		self._path = path
		self._encoding = encoding
		self._size = os.stat(path).st_size

		self._pos = 0
		self._read_lines = 0
		self._actual_lines = 0

		self._cancel_pos = None

		self._handle = None

	@property
	def size(self):
		return self._size

	@property
	def pos(self):
		return self._pos

	@property
	def actual_lines(self):
		return self._actual_lines

	@property
	def read_lines(self):
		return self._read_lines

	@property
	def cancel_pos(self):
		return self._cancel_pos

	@property
	def active(self):
		return self._start is not None and self._handle is not None

	@property
	def path(self):
		return self._path

	def event_payload(self, incl_last=False):
		event_data = StoragePrintjob.event_payload(self, incl_last=incl_last)
		event_data["size"] = self.size
		return event_data

	def process(self, protocol, position=0, user=None, tags=None, **kwargs):
		Printjob.process(self, protocol, position=position, user=user, tags=tags, **kwargs)

		from octoprint.util import bom_aware_open
		self._handle = bom_aware_open(self._path, encoding=self._encoding, errors="replace")

		if position > 0:
			self._handle.seek(position)
			self._pos = position
		self.process_job_started(user=user, tags=tags)

	def cancel(self, error=False, user=None, tags=None, **kwargs):
		self._cancel_pos = self.pos
		super(LocalFilePrintjob, self).cancel(error=error, user=user, tags=tags, **kwargs)

	def get_next(self):
		from octoprint.util import to_unicode

		if self._handle is None:
			raise ValueError("File {} is not open for reading" % self._path)

		try:
			processed = None
			while processed is None:
				if self._handle is None:
					# file got closed just now
					self.process_job_done()
					return None
				line = to_unicode(self._handle.readline())

				# we need to manually keep track of our pos here since
				# codecs' readline will make our handle's tell not
				# return the actual number of bytes read, but also the
				# already buffered bytes (for detecting the newlines)
				self._pos += len(line)
				self._actual_lines += 1

				if not line:
					self.process_job_done()
					return None
				processed = self.process_line(line)

			self._read_lines += 1
			self.process_job_progress()
			return processed
		except Exception as e:
			self.cancel(error=True)
			self._logger.exception("Exception while processing line")
			raise e

	def process_line(self, line):
		return line

	def close(self):
		if self._handle is not None:
			try:
				self._handle.close()
			except Exception:
				pass
		self._handle = None

	def can_get_content(self):
		return True

	def get_content_generator(self):
		from octoprint.util import bom_aware_open
		with bom_aware_open(self._path, encoding=self._encoding, error="replace") as f:
			for line in f.readline():
				yield line

	def reset_job(self, success=True):
		super(LocalFilePrintjob, self).reset_job(success=success)
		self.close()
		self._pos = self._read_lines = 0

	def report_stats(self):
		elapsed = self.elapsed
		lines = self._read_lines

		if elapsed and lines:
			self._logger.info("Job processed in {:.3f}s ({} lines)".format(elapsed, lines))


class LocalGcodeFilePrintjob(LocalFilePrintjob):

	def can_process(self, protocol):
		return LocalGcodeFilePrintjob in protocol.supported_jobs

	def process_line(self, line):
		# TODO no dependency on protocol module
		from octoprint.comm.protocol.reprap.util import strip_comment

		# strip line
		processed = line.strip()

		# strip comments
		processed = strip_comment(processed)
		if not len(processed):
			return None

		# TODO apply offsets

		# return result
		return processed


class CopyJobMixin(object):
	pass


class LocalGcodeStreamjob(LocalGcodeFilePrintjob, CopyJobMixin):

	exclusive = True

	@classmethod
	def from_job(cls, job, remote):
		if not isinstance(job, LocalGcodeFilePrintjob):
			raise ValueError("job must be a LocalGcodeFilePrintjob")

		path = job._path
		storage = job._storage
		path_in_storage = job._path_in_storage
		name = job._name
		user = job._user
		encoding = job._encoding
		event_data = job._event_data

		return cls(remote, path, storage, path_in_storage,
		           name=name, user=user, encoding=encoding, event_data=event_data)

	def __init__(self, remote, *args, **kwargs):
		super(LocalGcodeStreamjob, self).__init__(*args, **kwargs)
		self._remote = remote

	@property
	def remote(self):
		return self._remote

	def process(self, protocol, position=0, user=None, tags=None, **kwargs):
		super(LocalGcodeStreamjob, self).process(protocol, position=position, user=user, tags=tags, **kwargs)
		self._protocol.record_file(self._remote)

	def process_job_done(self, user=None, tags=None, **kwargs):
		self._protocol.stop_recording_file()
		super(LocalGcodeStreamjob, self).process_job_done(user=user, tags=tags, **kwargs)

	def process_job_failed(self, **kwargs):
		self._protocol.stop_recording_file()
		super(LocalGcodeStreamjob, self).process_job_failed(**kwargs)

	def process_job_cancelled(self, user=None, tags=None, **kwargs):
		self._protocol.stop_recording_file()
		self._protocol.delete_file(self.remote)
		super(LocalGcodeStreamjob, self).process_job_cancelled(user=user, tags=tags, **kwargs)

	def can_process(self, protocol):
		from octoprint.comm.protocol import FileStreamingProtocolMixin
		return LocalGcodeStreamjob in protocol.supported_jobs and isinstance(protocol, FileStreamingProtocolMixin) and isinstance(protocol, FileManagementProtocolMixin)

	def report_stats(self):
		elapsed = self.elapsed
		lines = self._read_lines

		if elapsed and lines:
			self._logger.info("Job processed in {:.3f}s ({} lines). Approx. {:.3f} lines/s, {:.3f} ms/line".format(elapsed,
			                                                                                                       lines,
			                                                                                                       float(lines) / float(elapsed),
			                                                                                                       float(elapsed) * 1000.0 / float(lines)))


class SDFilePrintjob(StoragePrintjob, FileAwareProtocolListener):

	parallel = True

	def __init__(self, path, status_interval=2.0, *args, **kwargs):
		name = path
		if name.startswith("/"):
			name = name[1:]

		StoragePrintjob.__init__(self,
		                         "sdcard",
		                         name,
		                         name=name,
		                         event_data=dict(name=name,
		                                         path=path,
		                                         origin="sdcard"))
		self._filename = path
		self._status_interval = status_interval

		self._status_timer = None
		self._active = False

		self._size = None
		self._last_pos = None

	@property
	def size(self):
		return self._size

	@property
	def pos(self):
		return self._last_pos

	@property
	def active(self):
		return self._start is not None and self._active

	@property
	def status_interval(self):
		return self._status_interval

	def can_process(self, protocol):
		from octoprint.comm.protocol import FileAwareProtocolMixin
		return SDFilePrintjob in protocol.supported_jobs and isinstance(protocol, FileAwareProtocolMixin)

	def process(self, protocol, position=0, user=None, tags=None, **kwargs):
		Printjob.process(self, protocol, position=position, user=user, tags=tags, **kwargs)

		self._protocol.register_listener(self)
		self._active = True
		self._last_pos = position

		self._protocol.start_file_print(self._filename, position=position, user=user, tags=tags, **kwargs)
		self._protocol.start_file_print_status_monitor()

	def pause(self, user=None, tags=None, **kwargs):
		super(SDFilePrintjob, self).pause(user=user, tags=tags, **kwargs)
		self._protocol.pause_file_print(user=user, tags=tags**kwargs)

	def resume(self, user=None, tags=None, **kwargs):
		super(SDFilePrintjob, self).resume(user=user, tags=tags, **kwargs)
		self._protocol.resume_file_print(user=user, tags=tags, **kwargs)

	def on_protocol_sd_status(self, protocol, pos, total):
		self._last_pos = pos
		self._size = total
		self.process_job_progress()

	def on_protocol_file_print_started(self, protocol, name, long_name, size, *args, **kwargs):
		self._size = size
		self.process_job_started(**kwargs)

	def on_protocol_file_print_done(self, protocol, *args, **kwargs):
		self._protocol.stop_file_print_status_monitor(**kwargs)
		self.process_job_done(**kwargs)

	def on_protocol_file_print_paused(self, protocol, *args, **kwargs):
		self._protocol.pause_file_print(**kwargs)

	def on_protocol_file_print_resumed(self, protocol, *args, **kwargs):
		self._protocol.resume_file_print(**kwargs)

	def reset_job(self, success=True):
		super(SDFilePrintjob, self).reset_job(success=success)
		self._active = False
		self._last_pos = None
		self._size = None

	def event_payload(self, incl_last=False):
		payload = Printjob.event_payload(self, incl_last=incl_last)
		payload["size"] = self.size
		return payload


class PrintjobListener(object):

	def on_job_started(self, job, suppress_script=False, *args, **kwargs):
		pass

	def on_job_done(self, job, suppress_script=False, *args, **kwargs):
		pass

	def on_job_failed(self, job, *args, **kwargs):
		pass

	def on_job_cancelling(self, job, firmware_error=None, *args, **kwargs):
		pass

	def on_job_cancelled(self, job, cancel_position=None, suppress_script=False, *args, **kwargs):
		pass

	def on_job_paused(self, job, pause_position=None, suppress_script=False, *args, **kwargs):
		pass

	def on_job_resumed(self, job, suppress_script=False, *args, **kwargs):
		pass

	def on_job_progress(self, job, *args, **kwargs):
		pass
