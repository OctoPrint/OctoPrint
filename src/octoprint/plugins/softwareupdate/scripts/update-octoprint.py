#!/bin/env python
from __future__ import absolute_import, print_function

__author__ = "Gina Haeussge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import errno
import sys

def _log_call(*lines):
	_log(lines, prefix=">", stream="call")


def _log_stdout(*lines):
	_log(lines, prefix=" ", stream="stdout")


def _log_stderr(*lines):
	_log(lines, prefix=" ", stream="stderr")


def _log(lines, prefix=None, stream=None):
	output_stream = sys.stdout
	if stream == "stderr":
		output_stream = sys.stderr

	for line in lines:
		print(u"{} {}".format(prefix, line.strip()), file=output_stream)


def _execute(command, **kwargs):
	import sarge

	if isinstance(command, (list, tuple)):
		joined_command = " ".join(command)
	else:
		joined_command = command
	_log_call(joined_command)

	kwargs.update(dict(async=True, stdout=sarge.Capture(), stderr=sarge.Capture()))

	p = sarge.run(command, **kwargs)
	p.wait_events()

	all_stdout = []
	all_stderr = []
	try:
		while p.returncode is None:
			line = p.stderr.readline(timeout=0.5)
			if line:
				_log_stderr(line)
				all_stderr.append(line)

			line = p.stdout.readline(timeout=0.5)
			if line:
				_log_stdout(line)
				all_stdout.append(line)

			p.commands[0].poll()

	finally:
		p.close()

	stderr = p.stderr.text
	if stderr:
		split_lines = stderr.split("\n")
		_log_stderr(*split_lines)
		all_stderr += split_lines

	stdout = p.stdout.text
	if stdout:
		split_lines = stdout.split("\n")
		_log_stdout(*split_lines)
		all_stdout += split_lines

	return p.returncode, all_stdout, all_stderr


def _get_git_executables():
	GITS = ["git"]
	if sys.platform == "win32":
		GITS = ["git.cmd", "git.exe"]
	return GITS


def _git(args, cwd, verbose=False, git_executable=None):
	if git_executable is not None:
		commands = [git_executable]
	else:
		commands = _get_git_executables()

	for c in commands:
		try:
			return _execute([c] + args, cwd=cwd)
		except EnvironmentError:
			e = sys.exc_info()[1]
			if e.errno == errno.ENOENT:
				continue
			if verbose:
				print("unable to run %s" % args[0])
				print(e)
			return None, None
	else:
		if verbose:
			print("unable to find command, tried %s" % (commands,))
		return None, None


def _python(args, cwd, python_executable, sudo=False):
	command = [python_executable] + args
	if sudo:
		command = ["sudo"] + command
	try:
		return _execute(command, cwd=cwd)
	except:
		return None, None


def update_source(git_executable, folder, target, force=False):
	print(">>> Running: git diff --shortstat")
	returncode, stdout, stderr = _git(["diff", "--shortstat"], folder, git_executable=git_executable)
	if returncode != 0:
		raise RuntimeError("Could not update, \"git diff\" failed with returncode %d: %s" % (returncode, stdout))
	if stdout and stdout.strip():
		# we got changes in the working tree, maybe from the user, so we'll now rescue those into a patch
		import time
		import os
		timestamp = time.strftime("%Y%m%d%H%M")
		patch = os.path.join(folder, "%s-preupdate.patch" % timestamp)

		print(">>> Running: git diff and saving output to %s" % timestamp)
		returncode, stdout, stderr = _git(["diff"], folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Could not update, installation directory was dirty and state could not be persisted as a patch to %s" % patch)

		with open(patch, "wb") as f:
			f.write(stdout)

		print(">>> Running: git reset --hard")
		returncode, stdout, stderr = _git(["reset", "--hard"], folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Could not update, \"git reset --hard\" failed with returncode %d: %s" % (returncode, stdout))

	print(">>> Running: git pull")
	returncode, stdout, stderr = _git(["pull"], folder, git_executable=git_executable)
	if returncode != 0:
		raise RuntimeError("Could not update, \"git pull\" failed with returncode %d: %s" % (returncode, stdout))

	if force:
		reset_command = ["reset"]
		reset_command += [target]

		print(">>> Running: git %s" % " ".join(reset_command))
		returncode, stdout, stderr = _git(reset_command, folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Error while updating, \"git %s\" failed with returncode %d: %s" % (" ".join(reset_command), returncode, stdout))


def install_source(python_executable, folder, user=False, sudo=False):
	print(">>> Running: python setup.py clean")
	returncode, stdout, stderr = _python(["setup.py", "clean"], folder, python_executable)
	if returncode != 0:
		print("\"python setup.py clean\" failed with returncode %d: %s" % (returncode, stdout))
		print("Continuing anyways")

	print(">>> Running: python setup.py install")
	args = ["setup.py", "install"]
	if user:
		args.append("--user")
	returncode, stdout, stderr = _python(args, folder, python_executable, sudo=sudo)
	if returncode != 0:
		raise RuntimeError("Could not update, \"python setup.py install\" failed with returncode %d: %s" % (returncode, stdout))


def parse_arguments():
	import argparse

	parser = argparse.ArgumentParser(prog="update-octoprint.py")

	parser.add_argument("--git", action="store", type=str, dest="git_executable",
	                    help="Specify git executable to use")
	parser.add_argument("--python", action="store", type=str, dest="python_executable",
	                    help="Specify python executable to use")
	parser.add_argument("--force", action="store_true", dest="force",
	                    help="Set this to force the update to only the specified version (nothing newer)")
	parser.add_argument("--sudo", action="store_true", dest="sudo",
	                    help="Install with sudo")
	parser.add_argument("--user", action="store_true", dest="user",
	                    help="Install to the user site directory instead of the general site directory")
	parser.add_argument("folder", type=str,
	                    help="Specify the base folder of the OctoPrint installation to update")
	parser.add_argument("target", type=str,
	                    help="Specify the commit or tag to which to update")

	args = parser.parse_args()

	return args

def main():
	args = parse_arguments()

	git_executable = None
	if args.git_executable:
		git_executable = args.git_executable

	python_executable = sys.executable
	if args.python_executable:
		python_executable = args.python_executable

	folder = args.folder
	target = args.target

	import os
	if not os.access(folder, os.W_OK):
		raise RuntimeError("Could not update, base folder is not writable")

	update_source(git_executable, folder, target, force=args.force)
	install_source(python_executable, folder, user=args.user, sudo=args.sudo)

if __name__ == "__main__":
	main()
