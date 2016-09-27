#!/bin/env python
from __future__ import absolute_import

__author__ = "Gina Haeussge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import errno
import subprocess
import sys


def _get_git_executables():
	GITS = ["git"]
	if sys.platform == "win32":
		GITS = ["git.cmd", "git.exe"]
	return GITS


def _git(args, cwd, hide_stderr=False, verbose=False, git_executable=None):
	if git_executable is not None:
		commands = [git_executable]
	else:
		commands = _get_git_executables()

	for c in commands:
		try:
			p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
			                     stderr=(subprocess.PIPE if hide_stderr
			                             else None))
			break
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

	stdout = p.communicate()[0].strip()
	if sys.version >= '3':
		stdout = stdout.decode()

	if p.returncode != 0:
		if verbose:
			print("unable to run %s (error)" % args[0])

	return p.returncode, stdout


def _python(args, cwd, python_executable, sudo=False):
	command = [python_executable] + args
	if sudo:
		command = ["sudo"] + command
	try:
		p = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE,
		                     stderr=subprocess.PIPE)
	except:
		return None, None

	stdout = p.communicate()[0].strip()
	if sys.version >= "3":
		stdout = stdout.decode()

	return p.returncode, stdout


def _rescue_changes(git_executable, folder):
	print(">>> Running: git diff --shortstat")
	returncode, stdout = _git(["diff", "--shortstat"], folder, git_executable=git_executable)
	if returncode != 0:
		raise RuntimeError("Could not update, \"git diff\" failed with returncode %d: %s" % (returncode, stdout))
	if stdout and stdout.strip():
		# we got changes in the working tree, maybe from the user, so we'll now rescue those into a patch
		import time
		import os
		timestamp = time.strftime("%Y%m%d%H%M")
		patch = os.path.join(folder, "%s-preupdate.patch" % timestamp)

		print(">>> Running: git diff and saving output to %s" % timestamp)
		returncode, stdout = _git(["diff"], folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Could not update, installation directory was dirty and state could not be persisted as a patch to %s" % patch)

		with open(patch, "wb") as f:
			f.write(stdout)

		return True

	return False


def update_source(git_executable, folder, target, force=False, branch=None):
	if _rescue_changes(git_executable, folder):
		print(">>> Running: git reset --hard")
		returncode, stdout = _git(["reset", "--hard"], folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Could not update, \"git reset --hard\" failed with returncode %d: %s" % (returncode, stdout))

	print(">>> Running: git fetch")
	returncode, stdout = _git(["fetch"], folder, git_executable=git_executable)
	if returncode != 0:
		raise RuntimeError("Could not update, \"git fetch\" failed with returncode %d: %s" % (returncode, stdout))
	print(stdout)

	if branch is not None and branch.strip() != "":
		print(">>> Running: git checkout {}".format(branch))
		returncode, stdout = _git(["checkout", branch], folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Could not update, \"git checkout\" failed with returncode %d: %s" % (returncode, stdout))

	print(">>> Running: git pull")
	returncode, stdout = _git(["pull"], folder, git_executable=git_executable)
	if returncode != 0:
		raise RuntimeError("Could not update, \"git pull\" failed with returncode %d: %s" % (returncode, stdout))
	print(stdout)

	if force:
		reset_command = ["reset", "--hard"]
		reset_command += [target]

		print(">>> Running: git %s" % " ".join(reset_command))
		returncode, stdout = _git(reset_command, folder, git_executable=git_executable)
		if returncode != 0:
			raise RuntimeError("Error while updating, \"git %s\" failed with returncode %d: %s" % (" ".join(reset_command), returncode, stdout))
		print(stdout)


def install_source(python_executable, folder, user=False, sudo=False):
	print(">>> Running: python setup.py clean")
	returncode, stdout = _python(["setup.py", "clean"], folder, python_executable)
	if returncode != 0:
		print("\"python setup.py clean\" failed with returncode %d: %s" % (returncode, stdout))
		print("Continuing anyways")
	print(stdout)

	print(">>> Running: python setup.py install")
	args = ["setup.py", "install"]
	if user:
		args.append("--user")
	returncode, stdout = _python(args, folder, python_executable, sudo=sudo)
	if returncode != 0:
		raise RuntimeError("Could not update, \"python setup.py install\" failed with returncode %d: %s" % (returncode, stdout))
	print(stdout)


def parse_arguments():
	import argparse

	boolean_trues = ["true", "yes", "1"]
	boolean_falses = ["false", "no", "0"]

	parser = argparse.ArgumentParser(prog="update-octoprint.py")

	parser.add_argument("--git", action="store", type=str, dest="git_executable",
	                    help="Specify git executable to use")
	parser.add_argument("--python", action="store", type=str, dest="python_executable",
	                    help="Specify python executable to use")
	parser.add_argument("--force", action="store", type=lambda x: x in boolean_trues,
	                    dest="force", default=False,
	                    help="Set this to true to force the update to only the specified version (nothing newer, nothing older)")
	parser.add_argument("--sudo", action="store_true", dest="sudo",
	                    help="Install with sudo")
	parser.add_argument("--user", action="store_true", dest="user",
	                    help="Install to the user site directory instead of the general site directory")
	parser.add_argument("--branch", action="store", type=str, dest="branch", default=None,
	                    help="Specify the branch to make sure is checked out")
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

	import os
	if not os.access(folder, os.W_OK):
		raise RuntimeError("Could not update, base folder is not writable")

	update_source(git_executable, folder, args.target, force=args.force, branch=args.branch)
	install_source(python_executable, folder, user=args.user, sudo=args.sudo)

if __name__ == "__main__":
	main()
