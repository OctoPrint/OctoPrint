#!/bin/sh

SCRIPTDIR=`dirname "$0"`
RESDIR=${SCRIPTDIR}/../Resources/

#run the path_helper to set the $PATH for accessing python
if [ -x /usr/libexec/path_helper ]; then
	eval `/usr/libexec/path_helper -s`
fi

displayMessage()
{
	/usr/bin/osascript > /dev/null <<-EOF
tell application "System Events"
	activate
	display dialog "$@" buttons {"Ok"}
end tell
EOF
}

#Testing for python2.7, which we need and is not always installed on MacOS 1.6
PY="python2.7"
$PY -c ''
if [ $? != 0 ]; then
	displayMessage "Python 2.7 is missing from your system. Cura requires Python2.7.\nStarting the installer" $PATH
	#TODO: Install python2.7
	$PY -c ''
	if [ $? != 0 ]; then
		displayMessage "Failed to install python2.7"
		exit 1
	fi
fi

#Next check for numpy, numpy does not always run under 64bit, so we need to check if we need to use "arch -i386"
$PY -c 'import numpy' 2> /dev/null
if [ $? != 0 ]; then
	PY="arch -i386 python2.7"
	$PY -c 'import numpy'
	if [ $? != 0 ]; then
		displayMessage "Numpy is missing from your system, this is required.\nStarting the installer"
		#TODO: Install numpy
		
		#After installing numpy, we need to check if we need to use arch -386 again
		PY="python2.7"
		$PY -c 'import numpy'
		if [ $? != 0 ]; then
			PY="arch -i386 python2.7"
			$PY -c 'import numpy'
			if [ $? != 0 ]; then
				displayMessage "Failed to install numpy."
				exit 1
			fi
		fi
	fi
fi

#Check for wxPython
$PY -c 'import wx'
if [ $? != 0 ]; then
	displayMessage "wxPython is missing from your system. Cura requires wxPython.\nStarting the installer"
	#TODO: Start wxPython installer
	$PY -c 'import wx'
	if [ $? != 0 ]; then
		displayMessage "Failed to properly install wxPython."
		exit 1
	fi
fi

#Check for PyOpenGL
$PY -c 'import OpenGL'
if [ $? != 0 ]; then
	displayMessage "PyOpenGL is missing from your system. Cura requires PyOpenGL.\nStarting installation"
	#TODO: Install PyOpenGL
	$PY -c 'import OpenGL'
	if [ $? != 0 ]; then
		displayMessage "Failed to properly install PyOpenGL."
		exit 1
	fi
fi

#Check for pyserial
$PY -c 'import serial'
if [ $? != 0 ]; then
	displayMessage "PySerial is missing from your system. Cura requires PySerial.\nStarting installation"
	#TODO: Install PySerial
	$PY -c 'import serial'
	if [ $? != 0 ]; then
		displayMessage "Failed to properly install PySerial."
		exit 1
	fi
fi

#All checks passed, start Cura
$PY "${RESDIR}Cura/cura.py" &
sleep 1

exit 0
