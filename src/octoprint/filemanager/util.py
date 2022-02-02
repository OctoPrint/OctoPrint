__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import io
import os

from octoprint import UMASK
from octoprint.util import atomic_write


class AbstractFileWrapper:
    """
    Wrapper for file representations to save to storages.

    Arguments:
        filename (str): The file's name
    """

    DEFAULT_PERMISSIONS = 0o664

    def __init__(self, filename):
        self.filename = filename

    def save(self, path, permissions=None):
        """
        Saves the file's content to the given absolute path.

        Arguments:
            path (str): The absolute path to where to save the file
            permissions (int): The permissions to set on the file
        """
        raise NotImplementedError()

    def stream(self):
        """
        Returns a Python stream object (subclass of io.IOBase) representing the file's contents.

        Returns:
            io.IOBase: The file's contents as a stream.
        """
        raise NotImplementedError()


class DiskFileWrapper(AbstractFileWrapper):
    """
    An implementation of :class:`.AbstractFileWrapper` that wraps an actual file on disk. The `save` implementations
    will either copy the file to the new path (preserving file attributes) or -- if `move` is `True` (the default) --
    move the file.

    Arguments:
        filename (str): The file's name
        path (str): The file's absolute path
        move (boolean): Whether to move the file upon saving (True, default) or copying.
    """

    def __init__(self, filename, path, move=True):
        AbstractFileWrapper.__init__(self, filename)
        self.path = path
        self.move = move

    def save(self, path, permissions=None):
        import shutil

        if self.move:
            shutil.move(self.path, path)
        else:
            shutil.copy2(self.path, path)

        if permissions is None:
            permissions = self.DEFAULT_PERMISSIONS & ~UMASK
        os.chmod(path, permissions)

    def stream(self):
        return open(self.path, "rb")


class StreamWrapper(AbstractFileWrapper):
    """
    A wrapper allowing processing of one or more consecutive streams.

    Arguments:
        *streams: One or more :py:class:`io.IOBase` streams to process one after another to save to storage.
    """

    def __init__(self, filename, *streams):
        if not len(streams) > 0:
            raise ValueError("Need at least one stream to wrap")

        AbstractFileWrapper.__init__(self, filename)
        self.streams = streams

    def save(self, path, permissions=None):
        """
        Will dump the contents of all streams provided during construction into the target file, in the order they were
        provided.
        """
        import shutil

        with atomic_write(path, mode="wb") as dest:
            for source in self.streams:
                shutil.copyfileobj(source, dest)
        if permissions is None:
            permissions = self.DEFAULT_PERMISSIONS & ~UMASK
        os.chmod(path, permissions)

    def stream(self):
        """
        If more than one stream was provided to the constructor, will return a :class:`.MultiStream` wrapping all
        provided streams in the order they were provided, else the first and only stream is returned directly.
        """
        if len(self.streams) > 1:
            return MultiStream(*self.streams)
        else:
            return self.streams[0]


class MultiStream(io.RawIOBase):
    """
    A stream implementation which when read reads from multiple streams, one after the other, basically concatenating
    their contents in the order they are provided to the constructor.

    Arguments:
        *streams: One or more :py:class:`io.IOBase` streams to concatenate.
    """

    def __init__(self, *streams):
        super().__init__()
        self.streams = streams
        self.current_stream = 0

    def read(self, n=-1):
        if n == 0:
            return b""

        if len(self.streams) == 0:
            return b""

        while self.current_stream < len(self.streams):
            stream = self.streams[self.current_stream]

            result = stream.read(n)
            if result is None or len(result) != 0:
                return result
            else:
                self.current_stream += 1

        return b""

    def readinto(self, b):
        n = len(b)
        read = self.read(n)
        b[: len(read)] = read
        return len(read)

    def close(self):
        for stream in self.streams:
            try:
                stream.close()
            except Exception:
                pass

    def readable(self, *args, **kwargs):
        return True

    def seekable(self, *args, **kwargs):
        return False

    def writable(self, *args, **kwargs):
        return False


class LineProcessorStream(io.RawIOBase):
    """
    While reading from this stream the provided `input_stream` is read line by line, calling the (overridable) method
    :meth:`.process_line` for each read line.

    Sub classes can thus modify the contents of the `input_stream` in line, while it is being read. Keep in mind that
    ``process_line`` will receive the line as a byte stream - if underlying code needs to operate on unicode you'll need
    to do the decoding yourself.

    Arguments:
        input_stream (io.RawIOBase): The stream to process on the fly.
    """

    def __init__(self, input_stream):
        super().__init__()
        self.input_stream = io.BufferedReader(input_stream)
        self.leftover = bytearray()

    def read(self, n=-1):
        if n == 0:
            return b""

        result = bytearray()
        while len(result) < n or n == -1:
            # add left over from previous loop
            bytes_left = (n - len(result)) if n != -1 else -1
            if bytes_left != -1 and bytes_left < len(self.leftover):
                # only s
                result += self.leftover[:bytes_left]
                self.leftover = self.leftover[bytes_left:]
                break
            else:
                result += self.leftover
                self.leftover = bytearray()

            # read one line from the underlying stream
            processed_line = None
            while processed_line is None:
                line = self.input_stream.readline()
                if not line:
                    break
                processed_line = self.process_line(line)
            if processed_line is None:
                break

            bytes_left = (n - len(result)) if n != -1 else -1
            if bytes_left != -1 and bytes_left < len(processed_line):
                result += processed_line[:bytes_left]
                self.leftover = processed_line[bytes_left:]
                break
            else:
                result += processed_line

        return bytes(result)

    def readinto(self, b):
        n = len(b)
        read = self.read(n)
        b[: len(read)] = read
        return len(read)

    def process_line(self, line):
        """
        Called from the `read` Method of this stream with each line read from `self.input_stream`.

        By returning ``None`` the line will not be returned from the read stream, effectively being stripped from the
        wrapper `input_stream`.

        Arguments:
            line (bytes): The line as read from `self.input_stream` in byte representation

        Returns:
            bytes or None: The processed version of the line (might also be multiple lines), or None if the line is to be
                stripped from the processed stream.
        """
        return line

    def close(self):
        self.input_stream.close()

    def readable(self, *args, **kwargs):
        return True

    def seekable(self, *args, **kwargs):
        return False

    def writable(self, *args, **kwargs):
        return False
