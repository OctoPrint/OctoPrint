from __future__ import absolute_import

import os
import sys
from Cura.util import resources

def getVersion(getGitVersion = True):
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	if hasattr(sys, 'frozen'):
		versionFile = os.path.normpath(os.path.join(resources.resourceBasePath, "version"))
	else:
		versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../version"))
	if os.path.exists(gitPath):
		if not getGitVersion:
			return "dev"
		f = open(gitPath + "/refs/heads/master", "r")
		version = f.readline()
		f.close()
		return version.strip()
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	return "?"

def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	return os.path.exists(gitPath)

if __name__ == '__main__':
	print(getVersion())

