from setuptools import setup

def run_checks():
	from distutils.command.install import install as cmd_install
	from distutils.dist import Distribution
	import sys
	import os

	cmd = cmd_install(Distribution())
	cmd.finalize_options()

	install_dir = cmd.install_lib
	virtual_env = hasattr(sys, "real_prefix")
	writable = os.access(install_dir, os.W_OK)

	print("!!! PIP_INSTALL_DIR={}".format(install_dir))
	print("!!! PIP_VIRTUAL_ENV={}".format(virtual_env))
	print("!!! PIP_WRITABLE={}".format(writable))
	sys.stdout.flush()

def parameters():
	run_checks()

	return dict(
		name="OctoPrint-PipTestBalloon",
		version="1.0",
		description="Just a test balloon to check a couple of pip related settings"
	)

setup(**parameters())
