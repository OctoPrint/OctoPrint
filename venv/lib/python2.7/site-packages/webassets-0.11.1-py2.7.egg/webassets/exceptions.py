__all__ = ('BundleError', 'BuildError', 'FilterError',
           'EnvironmentError', 'ImminentDeprecationWarning')


class EnvironmentError(Exception):
    pass


class BundleError(Exception):
    pass


class BuildError(BundleError):
    pass


class FilterError(BuildError):
    pass


class ImminentDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+.

    With webassets mainly targeting developers working directly with
    the library, it makes sense to force deprecation warnings on them.
    There should be no end users who will be bothered with them.

    Plus, we tend to remove rather quickly, so it's important devs
    get to see this.
    """
    pass
