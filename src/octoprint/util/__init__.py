# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import os
import traceback
import sys
import time
import re
import tempfile

from octoprint.settings import settings


def getFormattedSize(num):
	"""
	Taken from http://stackoverflow.com/a/1094933/2028598
	"""
	for x in ["bytes","KB","MB","GB"]:
		if num < 1024.0:
			return "%3.1f%s" % (num, x)
		num /= 1024.0
	return "%3.1f%s" % (num, "TB")


def isAllowedFile(filename, extensions):
	return "." in filename and filename.rsplit(".", 1)[1] in extensions


def getFormattedTimeDelta(d):
	if d is None:
		return None
	hours = d.seconds // 3600
	minutes = (d.seconds % 3600) // 60
	seconds = d.seconds % 60
	return "%02d:%02d:%02d" % (hours, minutes, seconds)


def getFormattedDateTime(d):
	if d is None:
		return None

	return d.strftime("%Y-%m-%d %H:%M")


def getClass(name):
	"""
	Taken from http://stackoverflow.com/a/452981/2028598
	"""
	parts = name.split(".")
	module = ".".join(parts[:-1])
	m = __import__(module)
	for comp in parts[1:]:
		m = getattr(m, comp)
	return m


def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../../.git"))
	return os.path.exists(gitPath)


def getExceptionString():
	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])


def getGitInfo():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../../.git"))
	if not os.path.exists(gitPath):
		return (None, None)

	headref = None
	with open(os.path.join(gitPath, "HEAD"), "r") as f:
		headref = f.readline().strip()

	if headref is None:
		return (None, None)

	headref = headref[len("ref: "):]
	branch = headref[headref.rfind("/") + 1:]
	with open(os.path.join(gitPath, headref)) as f:
		head = f.readline().strip()

	return (branch, head)


def getNewTimeout(type):
	now = time.time()

	if type not in ["connection", "detection", "communication"]:
		return now # timeout immediately for unknown timeout type

	return now + settings().getFloat(["serial", "timeout", type])


def getFreeBytes(path):
	"""
	Taken from http://stackoverflow.com/a/2372171/2028598
	"""
	if sys.platform == "win32":
		import ctypes
		freeBytes = ctypes.c_ulonglong(0)
		ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(freeBytes))
		return freeBytes.value
	else:
		st = os.statvfs(path)
		return st.f_bavail * st.f_frsize


def getRemoteAddress(request):
	forwardedFor = request.headers.get("X-Forwarded-For", None)
	if forwardedFor is not None:
		return forwardedFor.split(",")[0]
	return request.remote_addr


def getDosFilename(input, existingFilenames, extension=None):
	if input is None:
		return None

	if extension is None:
		extension = "gco"

	filename, ext = input.rsplit(".", 1)
	return findCollisionfreeName(filename, extension, existingFilenames)


def findCollisionfreeName(input, extension, existingFilenames):
	filename = re.sub(r"\s+", "_", input.lower().translate(None, ".\"/\\[]:;=,"))

	counter = 1
	power = 1
	while counter < (10 * power):
		result = filename[:(6 - power + 1)] + "~" + str(counter) + "." + extension
		if result not in existingFilenames:
			return result
		counter += 1
		if counter == 10 * power:
			power += 1

	raise ValueError("Can't create a collision free filename")


def safeRename(old, new):
	"""
	Safely renames a file.

	On Windows this is achieved by first creating a backup file of the new file (if it
	already exists), thus moving it, then renaming the old into the new file and finally removing the backup. If
	anything goes wrong during those steps, the backup (if already there) will be renamed to its old name and thus
	the operation hopefully result in a no-op.

	On other operating systems the atomic os.rename function will be used instead.

	@param old the path to the old file to be renamed
	@param new the path to the new file to be created/replaced
	"""

	if sys.platform == "win32":
		fh, backup = tempfile.mkstemp()
		os.close(fh)

		try:
			if os.path.exists(new):
				silentRemove(backup)
				os.rename(new, backup)
			os.rename(old, new)
			os.remove(backup)
		except OSError:
			# if anything went wrong, try to rename the backup file to its original name
			if os.path.exists(backup):
				os.remove(new)
			os.rename(backup, new)
	else:
		# on anything else than windows it's ooooh so much easier...
		os.rename(old, new)


def silentRemove(file):
	"""
	Silently removes a file. Does not raise an error if the file doesn't exist.

	@param file the path of the file to be removed
	"""

	try:
		os.remove(file)
	except OSError:
		pass
