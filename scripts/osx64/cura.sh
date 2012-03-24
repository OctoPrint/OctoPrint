#!/bin/bash

python -c 'import OpenGL'
if [ $? != 0 ]; then
	echo "Requires PyOpenGL"
	echo " sudo easy_install PyOpenGL"
	exit 1
fi

python -c 'import wx'
if [ $? != 0 ]; then
	echo "Requires wx. Download and install (the Cocoa/64-bit variant) from:"
	echo " http://www.wxpython.org/download.php"
	exit 1
fi

python -c 'import serial'
if [ $? != 0 ]; then
	echo "Requires pyserial."
	echo " sudo easy_install pyserial"
	exit 1
fi

SCRIPT_DIR=`dirname $0`
python ${SCRIPT_DIR}/Cura/cura.py

