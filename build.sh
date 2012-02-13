#!/bin/bash

#############################
# CONFIGURATION
#############################


##Select the build target
BUILD_TARGET=win32
#BUILD_TARGET=linux
#BUILD_TARGET=osx64

##Do we need to create the final archive
ARCHIVE_FOR_DISTRIBUTION=1
##Which version name are we appending to the final archive
BUILD_NAME=Alpha4
TARGET_DIR=${BUILD_TARGET}-SkeinPyPy-${BUILD_NAME}

##Which versions of external programs to use
PYPY_VERSION=1.8
WIN_PORTABLE_PY_VERSION=2.7.2.1
WIN_PYSERIAL_VERSION=2.5

#############################
# Support functions
#############################
function checkTool
{
	if [ -z `which $1` ]; then
		echo "The $1 command must be somewhere in your \$PATH."
		echo "Fix your \$PATH or install $2"
		exit 1
	fi
}

#############################
# Actual build script
#############################

checkTool git "git: http://git-scm.com/"
checkTool curl "curl: http://curl.haxx.se/"
if [ $BUILD_TARGET = "win32" ]; then
	#Check if we have 7zip, needed to extract and packup a bunch of packages for windows.
	checkTool 7z "7zip: http://www.7-zip.org/"
fi
#For building under MacOS we need gnutar instead of tar
if [ -z `which gnutar` ]; then
	TAR=tar
else
	TAR=gnutar
fi

#############################
# Download all needed files.
#############################

if [ $BUILD_TARGET = "win32" ]; then
	#Get portable python for windows and extract it. (Linux and Mac need to install python themselfs)
	if [ ! -f "PortablePython_${WIN_PORTABLE_PY_VERSION}.exe" ]; then
		curl -L -O http://ftp.nluug.nl/languages/python/portablepython/v2.7/PortablePython_${WIN_PORTABLE_PY_VERSION}.exe
	fi
	if [ ! -f pyserial-${WIN_PYSERIAL_VERSION}.exe ]; then
		curl -L -O http://sourceforge.net/projects/pyserial/files/pyserial/${WIN_PYSERIAL_VERSION}/pyserial-${WIN_PYSERIAL_VERSION}.win32.exe/download
		mv download pyserial-${WIN_PYSERIAL_VERSION}.exe
	fi
	#Get pypy
	if [ ! -f "pypy-${PYPY_VERSION}-win32.zip" ]; then
		curl -L -O https://bitbucket.org/pypy/pypy/downloads/pypy-${PYPY_VERSION}-win32.zip
	fi
else
	if [ ! -f "pypy-${PYPY_VERSION}-${BUILD_TARGET}.tar.bz2" ]; then
		curl -L -O https://bitbucket.org/pypy/pypy/downloads/pypy-${PYPY_VERSION}-${BUILD_TARGET}.tar.bz2
	fi
fi

#Get our own version of Printrun
rm -rf Printrun
git clone git://github.com/daid/Printrun.git
rm -rf Printrun/.git

#############################
# Build the packages
#############################
rm -rf ${TARGET_DIR}
mkdir -p ${TARGET_DIR}

if [ $BUILD_TARGET = "win32" ]; then
	#For windows extract portable python to include it.
	7z x PortablePython_${WIN_PORTABLE_PY_VERSION}.exe \$_OUTDIR/App
	7z x PortablePython_${WIN_PORTABLE_PY_VERSION}.exe \$_OUTDIR/Lib/site-packages
	7z x pyserial-${WIN_PYSERIAL_VERSION}.exe PURELIB

	mkdir -p ${TARGET_DIR}/python
	mv \$_OUTDIR/App/* ${TARGET_DIR}/python
	mv \$_OUTDIR/Lib/site-packages/wx* ${TARGET_DIR}/python/Lib/site-packages/
	mv PURELIB/serial ${TARGET_DIR}/python/Lib
	rm -rf \$_OUTDIR
	rm -rf PURELIB
fi

#Extract pypy
if [ $BUILD_TARGET = "win32" ]; then
	7z x pypy-${PYPY_VERSION}-win32.zip -o${TARGET_DIR}
	mv ${TARGET_DIR}/pypy-${PYPY_VERSION} ${TARGET_DIR}/pypy
else
	cd ${TARGET_DIR}; $TAR -xjf ../pypy-${PYPY_VERSION}-${BUILD_TARGET}.tar.bz2; cd ..
	mv ${TARGET_DIR}/pypy-${PYPY_VERSION} ${TARGET_DIR}/pypy
fi

#add Skeinforge
cp -a SkeinPyPy ${TARGET_DIR}/SkeinPyPy

#add printrun
mv Printrun ${TARGET_DIR}/Printrun

#add script files
cp -a scripts/${BUILD_TARGET}/* $TARGET_DIR/

#add readme file
cp README ${TARGET_DIR}/README.txt

#package the result
if (( ${ARCHIVE_FOR_DISTRIBUTION} )); then
	if [ $BUILD_TARGET = "win32" ]; then
		cd ${TARGET_DIR}
		7z a ../SkeinPyPy_${BUILD_TARGET}_${BUILD_NAME}.zip *
		cd ..
	else
		echo "Archiving to ${TARGET_DIR}.tar.gz"
		$TAR cfp - ${TARGET_DIR} | gzip --best -c > ${TARGET_DIR}.tar.gz
	fi
else
	echo "Installed into ${TARGET_DIR}"
fi

