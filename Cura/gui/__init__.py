import os
import sys

numberOfLevelsDeepInPackageHierarchy = 1
packageFilePath = os.path.abspath(__file__)
for level in range( numberOfLevelsDeepInPackageHierarchy + 1 ):
	packageFilePath = os.path.dirname( packageFilePath )
if packageFilePath not in sys.path:
	sys.path.insert( 0, packageFilePath )
