#!/bin/bash

python -c 'import wx'
if [ $? != 0 ]; then
	echo "Requires wx python."
	exit 1
fi

python -c 'import serial'
if [ $? != 0 ]; then
	echo "Requires pyserial."
	exit 1
fi

SCRIPT_DIR=`dirname $0`
python ${SCRIPT_DIR}/Printrun/pronterface.py

