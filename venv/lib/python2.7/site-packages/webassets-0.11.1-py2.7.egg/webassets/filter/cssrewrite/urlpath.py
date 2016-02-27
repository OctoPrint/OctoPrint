# urlpath.py

# 0.1.0
# 2005/08/20

# Functions that handle url paths.
# Part of Pythonutils
# http://www.voidspace.org.uk/python/pythonutils.html

# Copyright Michael Foord, 2004 & 2005.
# Released subject to the BSD License
# Please see http://www.voidspace.org.uk/python/license.shtml

# For information about bugfixes, updates and support, please join the
# Pythonutils mailing list.
# http://groups.google.com/group/pythonutils/
# Comments, suggestions and bug reports welcome.
# Scripts maintained at http://www.voidspace.org.uk/python/index.shtml
# E-mail fuzzyman@voidspace.org.uk

from __future__ import print_function
import posixpath
import os
try:
    from urllib.request import url2pathname, pathname2url
except ImportError:
    from urllib import url2pathname, pathname2url

__all__ = [
    'nativejoin',
    'pathjoin',
    'relpathto',
    'tslash',
    'relpath'
    ]

def pathjoin(base, *paths):
    """
    Join paths to a base, observing pardir.

    If base doesn't *end* with '/' we assume it's a file rather than a directory.
        (so we get rid of it)
    """
    # XXXX will posixpath.join do all this anyway?
    if base and not base.endswith('/'):
        # get rid of the filename
        base = '/'.join(base.split('/')[:-1])
    base = tslash(base)
    path = (base,) + paths
    return posixpath.normpath(posixpath.join(*path))

def nativejoin(base, path):
    """
    Joins two paths - returning a native file path.

    Given a base path and a relative location, (in posix format)
    return a file path in a (relatively) OS native way.
    """
    return url2pathname(pathjoin(base, path))

def relpathto(thisdir, origin, dest):
    """
    Given two paths relative to a directory, work out a path from origin
    to destination.

    Assumes UNIX/URL type relative paths.
    If origin doesn't *end* with '/' we assume it's a file rather than a
    directory.

    If the same paths are passed in :
        if the path ends with ('/') then we return ''
        else we return the last part of the path (presumably a filename)

    If thisdir doesn't start with '/' then we add one
        (this makes the top level of thisdir our root directory)
    """
    orig_thisdir = thisdir
    if not thisdir.startswith('/'):
        thisdir = '/' + thisdir
    orig_abs = posixpath.normpath(posixpath.join(thisdir, origin))
    dest_abs = posixpath.normpath(posixpath.join(thisdir, dest))
    if origin.endswith('/') and not orig_abs.endswith('/'):
        orig_abs = orig_abs + '/'
    if dest.endswith('/') and not dest_abs.endswith('/'):
        dest_abs = dest_abs + '/'
#    print orig_abs, dest_abs
    #
    # if the first item is a filename, we want to get rid of it
    orig_list = orig_abs.split('/')[:-1]
    dest_list = dest_abs.split('/')
#    print orig_list, dest_list

    if orig_list[0] != dest_list[0]:
        # can't get here from there
        # XXXX raise exception?
        return dest
    #
    # find the location where the two paths start to differ.
    i = 0
    for start_seg, dest_seg in zip(orig_list, dest_list):
        if start_seg != dest_seg:
            break
        i += 1
    #
    # now i is the point where the two paths diverge;
    # need a certain number of "os.pardir"s to work up
    # from the origin to the point of divergence.
    segments = ['..'] * (len(orig_list) - i)
    # need to add the diverging part of dest_list.
    segments += dest_list[i:]
    if len(segments) == 0:
        # if they happen to be identical paths
        # identical directories
        if dest.endswith('/'):
            return ''
        # just the filename - the last part of dest
        return dest_list[-1]
    else:
        return '/'.join(segments)

def relpath(origin, dest):
    """Given two absolute paths, work out a path from origin to destination.

    Assumes UNIX/URL type relative paths.
    If origin doesn't *end* with '/' we assume it's a file rather than
    a directory.

    If the same paths are passed in :
        if the path ends with ('/') then we return ''
        else we return the last part of the path (presumably a filename)

    If origin or dest don't start with '/' then we add it.

    We are *assuming* relative paths on the same device
        (i.e. same top level directory)
    """
    if not origin.startswith('/'):
        origin = '/' + origin
    if not dest.startswith('/'):
        dest = '/' + dest
    #
    # if the first item is a filename, we want to get rid of it
    orig_list = origin.split('/')[:-1]
    dest_list = dest.split('/')
    #
    # find the location where the two paths start to differ.
    i = 0
    for start_seg, dest_seg in zip(orig_list, dest_list):
        if start_seg != dest_seg:
            break
        i += 1

    # now i is the point where the two paths diverge.
    # need a certain number of "os.pardir"s to work up
    # from the origin to the point of divergence.
    segments = ['..'] * (len(orig_list) - i)
    # need to add the diverging part of dest_list.
    segments += dest_list[i:]
    if len(segments) == 0:
        # if they happen to be identical paths
        # identical directories
        if dest.endswith('/'):
            return ''
        # just the filename - the last part of dest
        return dest_list[-1]
    else:
        return '/'.join(segments)

def tslash(apath):
    """Add a trailing slash to a path if it needs one.

    Doesn't use os.sep because you end up jiggered on windoze - when you
    want separators for URLs.
    """
    if (apath and
            apath != '.' and
            not apath.endswith('/') and
            not apath.endswith('\\')):
        return apath + '/'
    else:
        return apath

##############################################

def testJoin():
    thelist = [
        ('/', 'fish.html'),
        ('/dir/dir/', '../file'),
        ('dir/dir/', '../file'),
        ('dir/dir/', '../../file'),
        ('dir/dir/', '../../../file'),
        ('/dir/dir/', '../notherdir/file'),
        ('/dir/dir/', '../../notherdir/file'),
        ('dir/dir/', '../../notherdir/file'),
        ('dir/dir/', '../../../notherdir/file'),
        ('', '../path'),
    ]
    for entry in thelist:
        print(entry, '      ::        ', pathjoin(*entry))
        print(entry, '      ::        ', nativejoin(*entry))
        print('\n')

def testRelpathto():
    thedir = '//toplevel/dirone/dirtwo/dirthree'
    thelist = [
        ('file1.html', 'file2.html'),
        ('file1.html', '../file2.html'),
        ('../file1.html', '../file2.html'),
        ('../file1.html', 'file2.html'),
        ('../fish1/fish2/', '../../sub1/sub2/'),
        ('../fish1/fish2/', 'sub1/sub2'),
        ('../../../fish1/fish2/', 'sub1/sub2/'),
        ('../../../fish1/fish2/', 'sub1/sub2/file1.html'),
   ]
    for orig, dest in thelist:
        print('(%s, %s)      : ' % (orig, dest), relpathto(thedir, orig, dest))

def testRelpathto2():
    thedir = 'section3/'
    thelist = [
        ('../archive/strangeindex1.html', 'article2.html'),
    ]
    for orig, dest in thelist:
        answer = relpathto(thedir, orig, dest)
        print('(%s, %s)      : ' % (orig, dest), answer)

def testRelpath():
    thelist = [
        ('/hello/fish/', 'bungles'),
    ]
    for orig, dest in thelist:
        answer = relpath(orig, dest)
        print('(%s, %s)      : ' % (orig, dest), answer)


if __name__ == '__main__':
    testJoin()
    testRelpathto()
    testRelpath()
#    testRelpathto2()

"""
TODO
====

More comprehensive tests.

CHANGELOG
2005/07/31
Can now pass mulitple args to ``pathjoin``.
Finalised as version 0.1.0

2005/06/18
Changes by Nicola Larosa
    Code cleanup
        lines shortened
        comments on line above code
        empty comments in empty lines

2005/05/28
Added relpath to __all__


TODO
Move into pythonutils
relpathto could call relpath (and so be shorter)
nativejoin could accept multiple paths
Could tslash be more elegant ?
"""
