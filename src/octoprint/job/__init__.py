from __future__ import absolute_import, unicode_literals


import logging
import os
import time
import copy

from octoprint.comm.protocol import ProtocolListener, FileAwareProtocolListener, ProtocolState

from octoprint.util.listener import ListenerAware

from abc import ABCMeta, abstractmethod, abstractproperty

from monotonic import monotonic

class Printjob(ProtocolListener, ListenerAware):
	__metaclass__ = ABCMeta

	parallel = False

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
		return monotonic() - self._start if self._start is not None else None

	@property
	def clean_elapsed(self):
		elapsed = self.elapsed
		if elapsed is None:
			return None
		return elapsed - self._lost_time

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

	def process(self, protocol, position=0, tags=None):
		self._start = monotonic()
		self._protocol = protocol
		self._protocol.register_listener(self)

	def cancel(self, error=False):
		if error:
			self.process_job_failed()
		else:
			self.process_job_cancelled()
		self._protocol.unregister_listener(self)
		self._protocol = None

	def get_next(self):
		return None

	def can_get_content(self):
		return False

	def get_content_generator(self):
		return None

	def event_payload(self):
		payload = copy.deepcopy(self._event_data)
		payload["user"] = self._user
		return payload

	def process_job_started(self):
		self.notify_listeners("on_job_started", self)

	def process_job_done(self):
		self.notify_listeners("on_job_done", self)
		self.reset_job()

	def process_job_failed(self):
		self.notify_listeners("on_job_failed", self)
		self.reset_job()

	def process_job_cancelling(self, firmware_error=None):
		self.notify_listeners("on_job_cancelling", self, firmware_error=firmware_error)

	def process_job_cancelled(self, cancel_position=None):
		self.notify_listeners("on_job_cancelled", self, cancel_position=cancel_position)
		self.reset_job()

	def process_job_paused(self, pause_position=None):
		self.notify_listeners("on_job_paused", self, pause_position=pause_position)

	def process_job_resumed(self):
		self.notify_listeners("on_job_resumed", self)

	def process_job_progress(self):
		self.notify_listeners("on_job_progress", self)

	def reset_job(self):
		self._start = None

	def on_protocol_state(self, protocol, old_state, new_state):
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

	def event_payload(self):
		payload = Printjob.event_payload(self)
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
	def active(self):
		return self._start is not None and self._handle is not None

	@property
	def path(self):
		return self._path

	def event_payload(self):
		event_data = StoragePrintjob.event_payload(self)
		event_data["size"] = self.size
		return event_data

	def process(self, protocol, position=0, tags=None):
		Printjob.process(self, protocol, position=position)

		from octoprint.util import bom_aware_open
		self._handle = bom_aware_open(self._path, encoding=self._encoding, errors="replace")

		if position > 0:
			self._handle.seek(position)
			self._pos = position
		self.process_job_started()

	def get_next(self):
		from octoprint.util import to_unicode

		if self._handle is None:
			raise ValueError("File {} is not open for reading" % self._path)

		try:
			processed = None
			while processed is None:
				if self._handle is None:
					# file got closed just now
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
			except:
				pass
		self._handle = None

	def can_get_content(self):
		return True

	def get_content_generator(self):
		from octoprint.util import bom_aware_open
		with bom_aware_open(self._path, encoding=self._encoding, error="replace") as f:
			for line in f.readline():
				yield line

	def reset_job(self):
		super(LocalFilePrintjob, self).reset_job()
		self.close()
		self._pos = self._read_lines = 0

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


class LocalGcodeStreamjob(LocalGcodeFilePrintjob):

	def can_process(self, protocol):
		from octoprint.comm.protocol import FileStreamingProtocolMixin
		return LocalGcodeStreamjob in protocol.supported_jobs and isinstance(protocol, FileStreamingProtocolMixin)

	def process_line(self, line):
		# we do not change anything for sd file streaming
		return line


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

	def process(self, protocol, position=0, tags=None):
		Printjob.process(self, protocol, position=position)

		self._protocol.register_listener(self)
		self._protocol.start_file_print(self._filename, position=position, tags=tags)
		self._active = True
		self._last_pos = position

		from octoprint.util import RepeatedTimer
		self._status_timer = RepeatedTimer(self._status_interval, self._query_status, condition=self._query_active)
		self._status_timer.start()

	def on_protocol_file_status(self, protocol, pos, total):
		self._last_pos = pos
		self._size = total
		self.process_job_progress()

	def on_protocol_file_print_started(self, protocol, name, size):
		self._size = size
		self.process_job_started()

	def on_protocol_file_print_done(self, protocol):
		self.process_job_done()

	def reset_job(self):
		self._active = False
		self._last_pos = None
		self._size = None

	def _query_status(self):
		if self._protocol.can_send():
			self._protocol.get_file_print_status()

	def _query_active(self):
		return self._active


class PrintjobListener(object):

	def on_job_started(self, job):
		pass

	def on_job_done(self, job):
		pass

	def on_job_failed(self, job):
		pass

	def on_job_cancelling(self, job, firmware_error=None):
		pass

	def on_job_cancelled(self, job, cancel_position=None):
		pass

	def on_job_paused(self, job, pause_position=None):
		pass

	def on_job_resumed(self, job):
		pass

	def on_job_progress(self, job):
		pass
