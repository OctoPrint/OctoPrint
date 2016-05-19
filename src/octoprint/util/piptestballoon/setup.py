from __future__ import print_function
import os
import sys

"""
This "python package" doesn't actually install. This is intenional. It is merely
used to figure out some information about the environment a specific pip call
is running under (installation dir, whether it belongs to a virtual environment,
whether the install location is writable by the current user), and for that it
only needs to be invoked by pip, the pip call doesn't have to be successful
however.

If an environment variable "TESTBALLOON_OUTPUT" is set, it will be used as location
to write a file with the figured out data to. Simply writing to stdout (the default
behaviour if no such environment variable is set) is sadly not going to work out
with versions of pip > 8.0.0, which capture all stdout output regardless of used
--verbose or --log flags.
"""

def produce_output(stream):
	from distutils.command.install import install as cmd_install
	from distutils.dist import Distribution

	cmd = cmd_install(Distribution())
	cmd.finalize_options()

	install_dir = cmd.install_lib
	virtual_env = hasattr(sys, "real_prefix")
	writable = os.access(install_dir, os.W_OK)

	print("PIP_INSTALL_DIR={}".format(install_dir), file=stream)
	print("PIP_VIRTUAL_ENV={}".format(virtual_env), file=stream)
	print("PIP_WRITABLE={}".format(writable), file=stream)
	stream.flush()


path = os.environ.get("TESTBALLOON_OUTPUT", None)
if path is not None:
	# environment variable set, write to a log
	path = os.path.abspath(path)
	with open(path, mode="w+b") as output:
		produce_output(output)
else:
	# write to stdout
	produce_output(sys.stdout)

# fail intentionally
sys.exit(-1)
