#!/bin/bash

python -c 'import OpenGL'
if [ $? != 0 ]; then
	echo "Requires PyOpenGL"
	echo " sudo easy_install-2.7 PyOpenGL"
	exit 1
fi

python -c 'import wx'
if [ $? != 0 ]; then
	echo "Requires wxPython"
	exit 1
fi

python -c 'import serial'
if [ $? != 0 ]; then
	echo "Requires pyserial."
	exit 1
fi

python -c 'import numpy'
if [ $? != 0 ]; then
	echo "Requires numpy."
	exit 1
fi

python -c 'import power'
if [ $? != 0 ]; then
	echo "Requires power module from https://github.com/GreatFruitOmsk/Power."
	exit 1
fi

SCRIPT_DIR=`dirname $0`
cd $SCRIPT_DIR
python -m Cura.cura $@
