import sys, os, subprocess

def hasExporer():
	if sys.platform == 'win32' or sys.platform == 'cygwin' or sys.platform == 'darwin':
		return True
	if sys.platform == 'linux2':
		if os.path.isfile('/usr/bin/nautilus'):
			return True
		if os.path.isfile('/usr/bin/dolphin'):
			return True
	return False

def openExporer(filename):
	if sys.platform == 'win32' or sys.platform == 'cygwin':
		subprocess.Popen(r'explorer /select,"%s"' % (filename))
	if sys.platform == 'darwin':
		subprocess.Popen(['open', os.path.split(filename)[0]])
	if sys.platform == 'linux2':
		if os.path.isfile('/usr/bin/nautilus'):
			subprocess.Popen(['/usr/bin/nautilus', os.path.split(filename)[0]])
		elif os.path.isfile('/usr/bin/dolphin'):
			subprocess.Popen(['/usr/bin/dolphin', os.path.split(filename)[0]])

