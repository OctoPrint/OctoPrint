# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Marc Hannappel <salandora@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import yaml
from yaml.dumper import SafeDumper
from yaml.loader import SafeLoader

from octoprint.groups import Group
from octoprint.permissions import OctoPermission

def OctoPermission_yaml_representer(dumper, data):
	return dumper.represent_scalar(u'!octopermission', repr(data))


def OctoPermission_yaml_constructor(loader, node):
	value = loader.construct_scalar(node)
	name = value[value.find('name=') + 5:]
	from octoprint.permissions import Permissions
	return Permissions.permission_by_name(name)


def group_yaml_representer(dumper, data):
	return dumper.represent_scalar(u'!group', repr(data))


def group_yaml_constructor(loader, node):
	value = loader.construct_scalar(node)
	name = value[value.find('name=') + 5:]
	from octoprint.server import groupManager
	return groupManager.findGroup(name)


yaml.add_representer(OctoPermission, OctoPermission_yaml_representer, Dumper=SafeDumper)
yaml.add_constructor(u'!octopermission', OctoPermission_yaml_constructor, Loader=SafeLoader)
yaml.add_representer(Group, group_yaml_representer, Dumper=SafeDumper)
yaml.add_constructor(u'!group', group_yaml_constructor, Loader=SafeLoader)
