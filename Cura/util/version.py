from __future__ import absolute_import
import __init__

import os

def getVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../version"))
	if os.path.exists(gitPath):
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

if __name__ == '__main__':
	print getVersion()

