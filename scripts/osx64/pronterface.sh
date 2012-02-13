#!/bin/bash

arch -arch i386 python2.7 -c 'import wx'
if [ $? != 0 ]; then
	echo "Requires wx. Download and install from:"
	echo " http://www.wxpython.org/download.php"
	exit 1
fi

python2.7 -c 'import serial'
if [ $? != 0 ]; then
	echo "Requires pyserial."
	echo " sudo easy_install-2.7 pyserial"
	exit 1
fi

SCRIPT_DIR=`dirname $0`
arch -arch i386 python2.7 ${SCRIPT_DIR}/Printrun/pronterface.py

