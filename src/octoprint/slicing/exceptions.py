# coding=utf-8
"""
Slicing related exceptions.

.. autoclass:: SlicingException

.. autoclass:: SlicingCancelled
   :show-inheritance:

.. autoclass:: SlicerException
   :show-inheritance:

.. autoclass:: UnknownSlicer
   :show-inheritance:

.. autoclass:: SlicerNotConfigured
   :show-inheritance:

.. autoclass:: ProfileException

.. autoclass:: UnknownProfile
   :show-inheritance:

.. autoclass:: ProfileAlreadyExists
   :show-inheritance:

"""

from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


class SlicingException(BaseException):
	"""
	Base exception of all slicing related exceptions.
	"""
	pass

class SlicingCancelled(SlicingException):
	"""
	Raised if a slicing job was cancelled.
	"""
	pass

class SlicerException(SlicingException):
	"""
	Base exception of all slicer related exceptions.

	.. attribute:: slicer

	   Identifier of the slicer for which the exception was raised.
	"""
	def __init__(self, slicer, *args, **kwargs):
		super(SlicingException, self).__init__(*args, **kwargs)
		self.slicer = slicer

class SlicerNotConfigured(SlicerException):
	"""
	Raised if a slicer is not yet configured but must be configured to proceed.
	"""
	def __init__(self, slicer, *args, **kwargs):
		super(SlicerException, self).__init__(slicer, *args, **kwargs)
		self.message = "Slicer not configured: {slicer}".format(slicer=slicer)

class UnknownSlicer(SlicerException):
	"""
	Raised if a slicer is unknown.
	"""
	def __init__(self, slicer, *args, **kwargs):
		super(SlicerException, self).__init__(slicer, *args, **kwargs)
		self.message = "No such slicer: {slicer}".format(slicer=slicer)

class ProfileException(BaseException):
	"""
	Base exception of all slicing profile related exceptions.

	.. attribute:: slicer

	   Identifier of the slicer to which the profile belongs.

	.. attribute:: profile

	   Identifier of the profile for which the exception was raised.
	"""
	def __init__(self, slicer, profile, *args, **kwargs):
		super(BaseException, self).__init__(*args, **kwargs)
		self.slicer = slicer
		self.profile = profile

class UnknownProfile(ProfileException):
	"""
	Raised if a slicing profile does not exist but must exist to proceed.
	"""
	def __init__(self, slicer, profile, *args, **kwargs):
		super(ProfileException, self).__init__(slicer, profile, *args, **kwargs)
		self.message = "Profile {profile} for slicer {slicer} does not exist".format(profile=profile, slicer=slicer)

class ProfileAlreadyExists(ProfileException):
	"""
	Raised if a slicing profile already exists and must not be overwritten.
	"""
	def __init__(self, slicer, profile, *args, **kwargs):
		super(ProfileException, self).__init__(slicer, profile, *args, **kwargs)
		self.message = "Profile {profile} for slicer {slicer} already exists".format(profile=profile, slicer=slicer)