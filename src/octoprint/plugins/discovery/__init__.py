# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os

import octoprint.plugin

default_settings = {
	"publicPort": None,
	"pathPrefix": None,
	"httpUsername": None,
	"httpPassword": None
}
s = octoprint.plugin.plugin_settings("discovery", defaults=default_settings)


class DiscoveryPlugin(octoprint.plugin.types.StartupPlugin):
	def __init__(self):
		self.logger = logging.getLogger("octoprint.plugins." + __name__)

		self.octoprint_sd_ref = None
		self.http_sd_ref = None

	##~~ TemplatePlugin API (part of SettingsPlugin)

	def get_template_vars(self):
		return dict(
			_settings_menu_entry="Network discovery"
		)

	def get_template_folder(self):
		return os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

	#~~ StartupPlugin API

	def on_startup(self, host, port):
		self._bonjour_register(host, port)

	#~~ SettingsPlugin API

	def on_settings_load(self):
		return {
			"publicPort": s.getInt(["publicPort"]),
			"pathPrefix": s.get(["pathPrefix"]),
			"httpUsername": s.get(["httpUsername"]),
			"httpPassword": s.get(["httpPassword"])
		}

	def on_settings_save(self, data):
		if "publicPort" in data and data["publicPort"]:
			s.setInt(["publicPort"], data["publicPort"])
		if "pathPrefix" in data and data["pathPrefix"]:
			s.set(["pathPrefix"], data["pathPrefix"])
		if "httpUsername" in data and data["httpUsername"]:
			s.set(["httpUsername"], data["httpUsername"])
		if "httpPassword" in data and data["httpPassword"]:
			s.set(["httpPassword"], data["httpPassword"])

	#~~ internals

	def _bonjour_register(self, host, port):
		import pybonjour
		import socket

		def register_callback(sd_ref, flags, error_code, name, reg_type, domain):
			if error_code == pybonjour.kDNSServiceErr_NoError:
				self.logger.info("Registered {name} for {reg_type} with domain {domain}".format(**locals()))

		if s.getInt(["publicPort"]):
			port = s.getInt(["publicPort"])

		prefix = s.globalGet(["server", "reverseProxy", "prefixFallback"])
		path = "/"
		if s.get(["pathPrefix"]):
			path = s.get(["pathPrefix"])
		elif prefix:
			path = prefix

		name = "OctoPrint instance on {}".format(socket.gethostname())

		self.octoprint_sd_ref = pybonjour.DNSServiceRegister(
			name=name,
			regtype='_octoprint._tcp',
			port=port,
			txtRecord=pybonjour.TXTRecord(self._create_octoprint_txt_record_dict()),
			callBack=register_callback
		)
		pybonjour.DNSServiceProcessResult(self.octoprint_sd_ref)

		self.http_sd_ref = pybonjour.DNSServiceRegister(
			name=name,
			regtype='_http._tcp',
			port=port,
			txtRecord=pybonjour.TXTRecord(self._create_base_txt_record_dict()),
			callBack=register_callback
		)
		pybonjour.DNSServiceProcessResult(self.http_sd_ref)

	def _create_octoprint_txt_record_dict(self):
		entries = self._create_base_txt_record_dict()

		import octoprint.server
		import octoprint.server.api

		entries.update(dict(
			version=octoprint.server.VERSION,
			api=octoprint.server.api.VERSION,
		))

		return entries

	def _create_base_txt_record_dict(self):
		# determine path entry
		path = "/"
		if s.get(["pathPrefix"]):
			path = s.get(["pathPrefix"])
		else:
			prefix = s.globalGet(["server", "reverseProxy", "prefixFallback"])
			if prefix:
				path = prefix

		# fetch username and password (if set)
		username = s.get(["httpUsername"])
		password = s.get(["httpPassword"])

		entries = dict(
			path=path
		)

		if username and password:
			entries.update(dict(u=username, p=password))

		return entries


__plugin_name__ = "Discovery"
__plugin_version__ = "0.1"
__plugin_description__ = "Makes the OctoPrint instance discoverable via Bonjour/Avahi/Zeroconf"
__plugin_implementations__ = []

def __plugin_check__():
	try:
		import pybonjour
	except:
		# no pybonjour available, we can't continue
		logging.getLogger("octoprint.plugins." + __name__).info("pybonjour is not installed, Discovery Plugin won't be available. Please manually install pybonjour and restart OctoPrint")
		return False

	global __plugin_implementations__
	__plugin_implementations__ = [DiscoveryPlugin(),]
	return True

