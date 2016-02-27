import glob
import os
import sys
import warnings

from pkginfo.distribution import Distribution
from pkginfo._compat import STRING_TYPES

class Installed(Distribution):

    def __init__(self, package, metadata_version=None):
        if isinstance(package, STRING_TYPES):
            self.package_name = package
            try:
                __import__(package)
            except ImportError:
                package = None
            else:
                package = sys.modules[package]
        else:
            self.package_name = package.__name__
        self.package = package
        self.metadata_version = metadata_version
        self.extractMetadata()

    def read(self):
        opj = os.path.join
        if self.package is not None:
            package = self.package.__package__
            if package is None:
                package = self.package.__name__
            pattern = '%s*.egg-info' % package
            file = getattr(self.package, '__file__', None)
            if file is not None:
                candidates = []
                def _add_candidate(where):
                    candidates.extend(glob.glob(where))
                for entry in sys.path:
                    if file.startswith(entry):
                        _add_candidate(opj(entry, 'EGG-INFO')) # egg?
                        _add_candidate(opj(entry, pattern)) # dist-installed?
                dir, name = os.path.split(self.package.__file__)
                _add_candidate(opj(dir, pattern))
                _add_candidate(opj(dir, '..', pattern))
                for candidate in candidates:
                    if os.path.isdir(candidate):
                        path = opj(candidate, 'PKG-INFO')
                    else:
                        path = candidate
                    if os.path.exists(path):
                        with open(path) as f:
                            return f.read()
        warnings.warn('No PKG-INFO found for package: %s' % self.package_name)
