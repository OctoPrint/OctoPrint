# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


class SlicingException(BaseException):
	pass

class SlicingCancelled(SlicingException):
	pass

class SlicerException(SlicingException):
	def __init__(self, slicer, *args, **kwargs):
		super(SlicingException, self).__init__(*args, **kwargs)
		self.slicer = slicer

class SlicerNotConfigured(SlicerException):
	def __init__(self, slicer, *args, **kwargs):
		super(SlicerException, self).__init__(slicer, *args, **kwargs)
		self.message = "Slicer not configured: {slicer}".format(slicer=slicer)

class UnknownSlicer(SlicerException):
	def __init__(self, slicer, *args, **kwargs):
		super(SlicerException, self).__init__(slicer, *args, **kwargs)
		self.message = "No such slicer: {slicer}".format(slicer=slicer)
