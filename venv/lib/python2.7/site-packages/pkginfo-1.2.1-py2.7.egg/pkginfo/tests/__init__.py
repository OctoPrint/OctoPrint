# requirements


def _checkSample(testcase, installed):
    try:
        import pkg_resources
    except ImportError: # no setuptools :(
        pass
    else:
        version = pkg_resources.require('pkginfo')[0].version
        testcase.assertEqual(installed.version, version)
    testcase.assertEqual(installed.name, 'pkginfo')
    testcase.assertEqual(installed.keywords,
                        'distribution sdist installed metadata' )
    testcase.assertEqual(list(installed.supported_platforms), [])

def _checkClassifiers(testcase, installed):
    testcase.assertEqual(list(installed.classifiers),
                         [
      'Intended Audience :: Developers',
      'License :: OSI Approved :: Python Software Foundation License',
      'Operating System :: OS Independent',
      'Programming Language :: Python :: 2.6',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3.2',
      'Programming Language :: Python :: 3.3',
      'Programming Language :: Python :: Implementation :: CPython',
      'Programming Language :: Python :: Implementation :: PyPy',
      'Topic :: Software Development :: Libraries :: Python Modules',
      'Topic :: System :: Software Distribution',
    ])


def _defaultMetadataVersion():
    import sys
    if sys.version_info[:2] > (2, 6):
        return '1.1'
    return '1.0'
