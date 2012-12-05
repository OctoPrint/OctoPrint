# coding=utf-8
from __future__ import absolute_import
import os
import sys

__all__ = ['getPathForResource', 'getPathForImage', 'getPathForMesh']


if sys.platform.startswith('darwin'):
	if hasattr(sys, 'frozen'):
		from Foundation import *
		imagesPath = os.path.join(NSBundle.mainBundle().resourcePath(), 'images')
		meshesPath = os.path.join(NSBundle.mainBundle().resourcePath(), 'images')
	else:
		imagesPath = os.path.join(os.path.dirname(__file__), "../images")
		meshesPath = os.path.join(os.path.dirname(__file__), "../images")
else:
	if hasattr(sys, 'frozen'):
		imagesPath = os.path.join(os.path.dirname(__file__), "../../images")
		meshesPath = os.path.join(os.path.dirname(__file__), "../../images")
	else:
		imagesPath = os.path.join(os.path.dirname(__file__), "../images")
		meshesPath = os.path.join(os.path.dirname(__file__), "../images")


def getPathForResource(dir, resource_name):
	assert os.path.isdir(dir), "{p} is not a directory".format(p=dir)
	path = os.path.normpath(os.path.join(dir, resource_name))
	assert os.path.isfile(path), "{p} is not a file.".format(p=path)
	return path

def getPathForImage(name):
	return getPathForResource(imagesPath, name)

def getPathForMesh(name):
	return getPathForResource(meshesPath, name)
