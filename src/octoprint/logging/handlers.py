# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

# noinspection PyCompatibility
import concurrent.futures
import logging.handlers
import os
import re
import time


class AsyncLogHandlerMixin(logging.Handler):
    def __init__(self, *args, **kwargs):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        super(AsyncLogHandlerMixin, self).__init__(*args, **kwargs)

    def emit(self, record):
        if getattr(self._executor, "_shutdown", False):
            return

        try:
            self._executor.submit(self._emit, record)
        except Exception:
            self.handleError(record)

    def _emit(self, record):
        # noinspection PyUnresolvedReferences
        super(AsyncLogHandlerMixin, self).emit(record)

    def close(self):
        self._executor.shutdown(wait=True)
        super(AsyncLogHandlerMixin, self).close()


class CleaningTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    def __init__(self, *args, **kwargs):
        kwargs["encoding"] = kwargs.get("encoding", "utf-8")

        super(CleaningTimedRotatingFileHandler, self).__init__(*args, **kwargs)

        # clean up old files on handler start
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)


class OctoPrintLogHandler(AsyncLogHandlerMixin, CleaningTimedRotatingFileHandler):
    rollover_callbacks = []

    def __init__(self, *args, **kwargs):
        kwargs["encoding"] = kwargs.get("encoding", "utf-8")
        super(OctoPrintLogHandler, self).__init__(*args, **kwargs)

    @classmethod
    def registerRolloverCallback(cls, callback, *args, **kwargs):
        cls.rollover_callbacks.append((callback, args, kwargs))

    def doRollover(self):
        super(OctoPrintLogHandler, self).doRollover()

        for rcb in self.rollover_callbacks:
            callback, args, kwargs = rcb
            callback(*args, **kwargs)


class OctoPrintStreamHandler(AsyncLogHandlerMixin, logging.StreamHandler):
    pass


class TriggeredRolloverLogHandler(
    AsyncLogHandlerMixin, logging.handlers.RotatingFileHandler
):

    do_rollover = False
    suffix_template = "%Y-%m-%d_%H-%M-%S"
    file_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")

    @classmethod
    def arm_rollover(cls):
        cls.do_rollover = True

    def __init__(self, *args, **kwargs):
        kwargs["encoding"] = kwargs.get("encoding", "utf-8")
        super(TriggeredRolloverLogHandler, self).__init__(*args, **kwargs)
        self.cleanupFiles()

    def shouldRollover(self, record):
        return self.do_rollover

    def getFilesToDelete(self):
        """
        Determine the files to delete when rolling over.
        """
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName + "."
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if type(self).file_pattern.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        result.sort()
        if len(result) < self.backupCount:
            result = []
        else:
            result = result[: len(result) - self.backupCount]
        return result

    def cleanupFiles(self):
        if self.backupCount > 0:
            for path in self.getFilesToDelete():
                os.remove(path)

    def doRollover(self):
        self.do_rollover = False

        if self.stream:
            self.stream.close()
            self.stream = None

        if os.path.exists(self.baseFilename):
            # figure out creation date/time to use for file suffix
            t = time.localtime(os.stat(self.baseFilename).st_mtime)
            dfn = self.baseFilename + "." + time.strftime(type(self).suffix_template, t)
            if os.path.exists(dfn):
                os.remove(dfn)
            os.rename(self.baseFilename, dfn)

        self.cleanupFiles()
        if not self.delay:
            self.stream = self._open()


class SerialLogHandler(TriggeredRolloverLogHandler):
    pass


class PluginTimingsLogHandler(TriggeredRolloverLogHandler):
    pass


class RecordingLogHandler(logging.Handler):
    def __init__(self, target=None, *args, **kwargs):
        super(RecordingLogHandler, self).__init__(*args, **kwargs)
        self._buffer = []
        self._target = target

    def emit(self, record):
        self._buffer.append(record)

    def setTarget(self, target):
        self._target = target

    def flush(self):
        if not self._target:
            return

        self.acquire()
        try:
            for record in self._buffer:
                self._target.handle(record)
            self._buffer = []
        finally:
            self.release()

    def close(self):
        self.flush()
        self.acquire()
        try:
            self._buffer = []
        finally:
            self.release()

    def __len__(self):
        return len(self._buffer)


# noinspection PyAbstractClass
class CombinedLogHandler(logging.Handler):
    def __init__(self, *handlers):
        logging.Handler.__init__(self)
        self._handlers = handlers

    def setHandlers(self, *handlers):
        self._handlers = handlers

    def handle(self, record):
        self.acquire()
        try:
            if self._handlers:
                for handler in self._handlers:
                    handler.handle(record)
        finally:
            self.release()
