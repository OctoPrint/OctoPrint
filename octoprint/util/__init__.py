# coding=utf-8
__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'

import re
import os

def getFormattedSize(num):
	"""
	 Taken from http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
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

def matchesGcode(line, gcode):
	return re.search("^%s(\D|$)" % gcode.strip(), line, re.I)

def getGitInfo():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
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