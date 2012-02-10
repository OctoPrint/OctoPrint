#!/bin/sh

#############################
# CONFIGURATION
#############################

PYPY_VERSION=1.8
WIN_PORTABLE_PY_VERSION=2.7.2.1
WIN_PYSERIAL_VERSION=2.5
BUILD_NAME=Alpha4

#############################
# Actual build script
#############################

#Check if we have 7zip, needed to extract and packup a bunch of packages.
7z > /dev/null 2>&1
if [ $? != 0 ]; then
	echo $0 requires 7zip to run.
	exit 1
fi

#############################
# Download all needed files.
#############################

#Get portable python for windows and extract it. (Linux and Mac need to install python themselfs)
if [ ! -f "PortablePython_${WIN_PORTABLE_PY_VERSION}.exe" ]; then
	wget http://ftp.nluug.nl/languages/python/portablepython/v2.7/PortablePython_${WIN_PORTABLE_PY_VERSION}.exe
fi
if [ ! -f pyserial-${WIN_PYSERIAL_VERSION}.exe ]; then
	wget http://sourceforge.net/projects/pyserial/files/pyserial/${WIN_PYSERIAL_VERSION}/pyserial-${WIN_PYSERIAL_VERSION}.win32.exe/download
	mv download pyserial-${WIN_PYSERIAL_VERSION}.exe
fi
#Get pypy
if [ ! -f "pypy-${PYPY_VERSION}-win32.zip" ]; then
	wget https://bitbucket.org/pypy/pypy/downloads/pypy-${PYPY_VERSION}-win32.zip
fi
if [ ! -f "pypy-${PYPY_VERSION}-linux.tar.bz2" ]; then
	wget https://bitbucket.org/pypy/pypy/downloads/pypy-${PYPY_VERSION}-linux.tar.bz2
fi
if [ ! -f "pypy-${PYPY_VERSION}-osx64.tar.bz2" ]; then
	wget https://bitbucket.org/pypy/pypy/downloads/pypy-${PYPY_VERSION}-osx64.tar.bz2
fi
#Get our own version of Printrun
rm -rf Printrun
git clone git://github.com/daid/Printrun.git
rm -rf Printrun/.git

#############################
# Build the packages
#############################
rm -rf target_win32 target_linux target_osx64
mkdir -p target_win32 target_linux target_osx64

7z x PortablePython_${WIN_PORTABLE_PY_VERSION}.exe \$_OUTDIR/App
7z x PortablePython_${WIN_PORTABLE_PY_VERSION}.exe \$_OUTDIR/Lib/site-packages
7z x pyserial-${WIN_PYSERIAL_VERSION}.exe PURELIB

mkdir -p target_win32/python
mv \$_OUTDIR/App/* target_win32/python
mv \$_OUTDIR/Lib/site-packages/wx* target_win32/python/Lib/site-packages/
mv PURELIB/serial target_win32/python/Lib
rm -rf \$_OUTDIR
rm -rf PURELIB

#Extract pypy
7z x pypy-${PYPY_VERSION}-win32.zip -otarget_win32
mv target_win32/pypy-${PYPY_VERSION} target_win32/pypy
cd target_linux; tar -xjf ../pypy-${PYPY_VERSION}-linux.tar.bz2; cd ..
mv target_linux/pypy-${PYPY_VERSION} target_linux/pypy
cd target_osx64; tar -xjf ../pypy-${PYPY_VERSION}-osx64.tar.bz2; cd ..
mv target_linux/pypy-${PYPY_VERSION} target_osx64/pypy

#add Skeinforge
cp -a SkeinPyPy target_win32/SkeinPyPy
cp -a SkeinPyPy target_linux/SkeinPyPy
cp -a SkeinPyPy target_osx64/SkeinPyPy

#add printrun
cp -a Printrun target_win32/Printrun
cp -a Printrun target_linux/Printrun
cp -a Printrun target_osx64/Printrun

#add windows batch files
echo "python\\python.exe SkeinPyPy\\skeinforge_application\\skeinforge.py" > target_win32/skeinforge.bat
echo "python\\python.exe printrun\\pronterface.py" > target_win32/printrun.bat

#add readme file
cp README target_win32/README.txt
cp README target_linux/README.txt
cp README target_osx64/README.txt

#package the result
cd target_win32
7z a ../SkeinPyPy_Win32_${BUILD_NAME}.zip *
cd ..
cd target_linux
7z a ../SkeinPyPy_Linux_${BUILD_NAME}.zip *
cd ..
cd target_osx64
7z a ../SkeinPyPy_MacOSX_${BUILD_NAME}.zip *
cd ..

