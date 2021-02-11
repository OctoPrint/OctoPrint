__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

from octoprint.comm.protocol import FileAwareProtocolListener

from . import Printjob, StoragePrintjob


class SDFilePrintjob(StoragePrintjob, FileAwareProtocolListener):

    parallel = True

    def __init__(self, path, status_interval=2.0, *args, **kwargs):
        name = path
        if name.startswith("/"):
            name = name[1:]

        StoragePrintjob.__init__(
            self,
            "sdcard",
            name,
            name=name,
            event_data={"name": name, "path": path, "origin": "sdcard"},
        )
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

        return SDFilePrintjob in protocol.supported_jobs and isinstance(
            protocol, FileAwareProtocolMixin
        )

    def process(self, protocol, position=0, user=None, tags=None, **kwargs):
        Printjob.process(
            self, protocol, position=position, user=user, tags=tags, **kwargs
        )

        self._protocol.register_listener(self)
        self._active = True
        self._last_pos = position

        self._protocol.start_file_print(
            self._filename,
            position=position,
            user=user,
            tags=tags,
            part_of_job=True,
            **kwargs
        )
        self._protocol.start_file_print_status_monitor()

    def pause(self, user=None, tags=None, **kwargs):
        super(SDFilePrintjob, self).pause(user=user, tags=tags, **kwargs)
        self._protocol.pause_file_print(user=user, tags=tags, part_of_job=True, **kwargs)

    def resume(self, user=None, tags=None, **kwargs):
        super(SDFilePrintjob, self).resume(user=user, tags=tags, **kwargs)
        self._protocol.resume_file_print(user=user, tags=tags, part_of_job=True, **kwargs)

    def on_protocol_sd_status(self, protocol, pos, total):
        self._last_pos = pos
        self._size = total
        self.process_job_progress()

    def on_protocol_file_print_started(
        self, protocol, name, long_name, size, *args, **kwargs
    ):
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
