# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging

from ..exceptions import ConfigurationInvalid, CannotCheckOffline
from ..util import execute

def get_latest(target, check, online=True):
	command = check.get("command")
	if command is None:
		raise ConfigurationInvalid("Update configuration for {} of type commandline needs command set and not None".format(target))

	if not online and not check.get("offline", False):
		raise CannotCheckOffline("{} isn't marked as 'offline' capable, but we are apparently offline right now".format(target))

	returncode, stdout, stderr = execute(command, evaluate_returncode=False)

	# We expect command line check commands to
	#
	# * have a return code of 0 if an update is available, a value != 0 otherwise
	# * return the display name of the new version as the final line on stdout
	# * return the display name of the current version as the next to final line on stdout
	#
	# Example output:
	# 1.1.0
	# 1.1.1
	#
	# 1.1.0 is the current version, 1.1.1 is the remote version. If only one line is output, it's taken to be the
	# display name of the new version

	stdout_lines = list(filter(lambda x: len(x.strip()), stdout.splitlines()))
	local_name = stdout_lines[-2] if len(stdout_lines) >= 2 else "unknown"
	remote_name = stdout_lines[-1] if len(stdout_lines) >= 1 else "unknown"
	is_current = returncode != 0

	information =dict(
		local=dict(
			name=local_name,
		    value=local_name,
		),
		remote=dict(
			name=remote_name,
			value=remote_name
		)
	)

	logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.github_commit")
	logger.debug("Target: %s, local: %s, remote: %s" % (target, local_name, remote_name))

	return information, is_current
