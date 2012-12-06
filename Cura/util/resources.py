# coding=utf-8
from __future__ import absolute_import
import os
import sys

__all__ = ['getPathForResource', 'getPathForImage', 'getPathForMesh']


if sys.platform.startswith('darwin'):
	if hasattr(sys, 'frozen'):
		from Foundation import *
		resourceBasePath = NSBundle.mainBundle().resourcePath()
	else:
		resourceBasePath = os.path.join(os.path.dirname(__file__), "../resources")
else:
	if hasattr(sys, 'frozen'):
		resourceBasePath = os.path.join(os.path.dirname(__file__), "../../resources")
	else:
		resourceBasePath = os.path.join(os.path.dirname(__file__), "../resources")

def getPathForResource(dir, subdir, resource_name):
	assert os.path.isdir(dir), "{p} is not a directory".format(p=dir)
	path = os.path.normpath(os.path.join(dir, subdir, resource_name))
	assert os.path.isfile(path), "{p} is not a file.".format(p=path)
	return path

def getPathForImage(name):
	return getPathForResource(resourceBasePath, 'images', name)

def getPathForMesh(name):
	return getPathForResource(resourceBasePath, 'meshes', name)

def getPathForFirmware(name):
	return getPathForResource(resourceBasePath, 'firmware', name)
