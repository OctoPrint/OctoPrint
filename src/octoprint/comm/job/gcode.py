__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 The OctoPrint Project - Released under terms of the AGPLv3 License"

from . import CopyJobMixin, LocalFilePrintjob


class LocalGcodeFilePrintjob(LocalFilePrintjob):
    def can_process(self, protocol):
        return LocalGcodeFilePrintjob in protocol.supported_jobs

    def process_line(self, line):
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

        return cls(
            remote,
            path,
            storage,
            path_in_storage,
            name=name,
            user=user,
            encoding=encoding,
            event_data=event_data,
        )

    def __init__(self, remote, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._remote = remote

    @property
    def remote(self):
        return self._remote

    def process(self, protocol, position=0, user=None, tags=None, **kwargs):
        super().process(protocol, position=position, user=user, tags=tags, **kwargs)
        self._protocol.record_file(self._remote)

    def process_job_done(self, user=None, tags=None, **kwargs):
        self._protocol.stop_recording_file()
        super().process_job_done(user=user, tags=tags, **kwargs)

    def process_job_failed(self, **kwargs):
        self._protocol.stop_recording_file()
        super().process_job_failed(**kwargs)

    def process_job_cancelled(self, user=None, tags=None, **kwargs):
        self._protocol.stop_recording_file()
        self._protocol.delete_file(self.remote)
        super().process_job_cancelled(user=user, tags=tags, **kwargs)

    def can_process(self, protocol):
        from octoprint.comm.protocol import (
            FileManagementProtocolMixin,
            FileStreamingProtocolMixin,
        )

        return (
            LocalGcodeStreamjob in protocol.supported_jobs
            and isinstance(protocol, FileStreamingProtocolMixin)
            and isinstance(protocol, FileManagementProtocolMixin)
        )

    def report_stats(self):
        elapsed = self.elapsed
        lines = self._read_lines

        if elapsed and lines:
            self._logger.info(
                "Job processed in {:.3f}s ({} lines). Approx. {:.3f} lines/s, {:.3f} ms/line".format(
                    elapsed,
                    lines,
                    float(lines) / float(elapsed),
                    float(elapsed) * 1000.0 / float(lines),
                )
            )
