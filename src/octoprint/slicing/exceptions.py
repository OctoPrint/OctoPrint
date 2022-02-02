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

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


class SlicingException(Exception):
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
        SlicingException.__init__(self, *args, **kwargs)
        self.slicer = slicer


class SlicerNotConfigured(SlicerException):
    """
    Raised if a slicer is not yet configured but must be configured to proceed.
    """

    def __init__(self, slicer, *args, **kwargs):
        SlicerException.__init__(self, slicer, *args, **kwargs)
        self.message = f"Slicer not configured: {slicer}"


class UnknownSlicer(SlicerException):
    """
    Raised if a slicer is unknown.
    """

    def __init__(self, slicer, *args, **kwargs):
        SlicerException.__init__(self, slicer, *args, **kwargs)
        self.message = f"No such slicer: {slicer}"


class ProfileException(Exception):
    """
    Base exception of all slicing profile related exceptions.

    .. attribute:: slicer

       Identifier of the slicer to which the profile belongs.

    .. attribute:: profile

       Identifier of the profile for which the exception was raised.
    """

    def __init__(self, slicer, profile, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.slicer = slicer
        self.profile = profile


class UnknownProfile(ProfileException):
    """
    Raised if a slicing profile does not exist but must exist to proceed.
    """

    def __init__(self, slicer, profile, *args, **kwargs):
        ProfileException.__init__(self, slicer, profile, *args, **kwargs)
        self.message = "Profile {profile} for slicer {slicer} does not exist".format(
            profile=profile, slicer=slicer
        )


class ProfileAlreadyExists(ProfileException):
    """
    Raised if a slicing profile already exists and must not be overwritten.
    """

    def __init__(self, slicer, profile, *args, **kwargs):
        ProfileException.__init__(self, slicer, profile, *args, **kwargs)
        self.message = "Profile {profile} for slicer {slicer} already exists".format(
            profile=profile, slicer=slicer
        )


class CouldNotDeleteProfile(ProfileException):
    """
    Raised if there is an unexpected error trying to delete a known profile.
    """

    def __init__(self, slicer, profile, cause=None, *args, **kwargs):
        ProfileException.__init__(self, slicer, profile, *args, **kwargs)

        self.cause = cause
        if cause:
            self.message = (
                "Could not delete profile {profile} for slicer {slicer}: {cause}".format(
                    profile=profile, slicer=slicer, cause=str(cause)
                )
            )
        else:
            self.message = (
                "Could not delete profile {profile} for slicer {slicer}".format(
                    profile=profile, slicer=slicer
                )
            )
