# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import logging
import os
import flask

import octoprint.plugin

default_settings = {
	"publicPort": None,
	"pathPrefix": None,
	"httpUsername": None,
	"httpPassword": None
}
s = octoprint.plugin.plugin_settings("discovery", defaults=default_settings)


def get_uuid():
	import uuid
	return str(uuid.uuid4())
UUID = get_uuid()
del get_uuid

def get_instance_name():
	import socket
	return "OctoPrint instance on {}".format(socket.gethostname())
INSTANCENAME = get_instance_name()
del get_instance_name


blueprint = flask.Blueprint("plugin.discovery", __name__, template_folder=os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates"))

@blueprint.route("/discovery.xml")
def discovery():
	logging.getLogger("octoprint.plugins." + __name__).info("Rendering discovery.xml")
	response = flask.make_response(flask.render_template("discovery.jinja2",
	                             friendlyName=INSTANCENAME,
	                             manufacturer="OctoPrint",
	                             manufacturerUrl="http://www.octoprint.org",
	                             modelDescription="Some funny description",
	                             modelName="Some funny name",
	                             uuid=UUID,
	                             presentationUrl=flask.url_for("index", _external=True)))
	response.headers['Content-Type'] = 'application/xml'
	return response


class DiscoveryPlugin(octoprint.plugin.types.StartupPlugin, octoprint.plugin.types.BlueprintPlugin, octoprint.plugin.SettingsPlugin):
	def __init__(self):
		self.logger = logging.getLogger("octoprint.plugins." + __name__)

		self.octoprint_sd_ref = None
		self.http_sd_ref = None

	##~~ BlueprintPlugin API

	def get_blueprint(self):
		return blueprint

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
		self._ssdp_register(port)

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

		def register_callback(sd_ref, flags, error_code, name, reg_type, domain):
			if error_code == pybonjour.kDNSServiceErr_NoError:
				self.logger.info("Registered {name} for {reg_type} with domain {domain}".format(**locals()))

		if s.getInt(["publicPort"]):
			port = s.getInt(["publicPort"])

		self.octoprint_sd_ref = pybonjour.DNSServiceRegister(
			name=INSTANCENAME,
			regtype='_octoprint._tcp',
			port=port,
			txtRecord=pybonjour.TXTRecord(self._create_octoprint_txt_record_dict()),
			callBack=register_callback
		)
		pybonjour.DNSServiceProcessResult(self.octoprint_sd_ref)

		self.http_sd_ref = pybonjour.DNSServiceRegister(
			name=INSTANCENAME,
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


	def _ssdp_register(self, port):
		import threading
		self._ssdp_monitor_thread = threading.Thread(target=self._ssdp_monitor, args=[port])
		self._ssdp_monitor_thread.daemon = True
		self._ssdp_monitor_thread.start()

	def _ssdp_notify(self, port, alive=True):
		import socket
		import netifaces

		def interface_addresses(family=netifaces.AF_INET):
			for interface in netifaces.interfaces():
				ifaddresses = netifaces.ifaddresses(interface)
				if family in ifaddresses:
					for ifaddress in ifaddresses[family]:
						yield ifaddress["addr"]

		for addr in interface_addresses():
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
				sock.bind((addr, 0))

				location = "http://{addr}:{port}/plugins/discovery/discovery.xml".format(addr=addr, port=port)

				self.logger.info("Sending NOTIFY alive")
				notify_message = "".join(["NOTIFY * HTTP/1.1\r\n", "Server: Python/2.7\r\n", "Cache-Control: max-age=900\r\n", "Location: {location}\r\n", "NTS: {nts}\r\n", "NT: upnp:rootdevice\r\n", "USN: uuid:{uuid}::upnp:rootdevice\r\n", "Host: 239.255.255.250:1900\r\n\r\n"])
				message = notify_message.format(uuid=UUID, location=location, nts="ssdp:alive" if alive else "ssdp:byebye")
				for _ in xrange(2):
					sock.sendto(message, ("239.255.255.250", 1900))

				try:
					sock.recv(1024)
				except socket.timeout:
					pass
			except Exception as e:
				pass

	def _ssdp_monitor(self, port):

		from BaseHTTPServer import BaseHTTPRequestHandler
		from httplib import HTTPResponse
		from StringIO import StringIO
		import socket
		import struct

		socket.setdefaulttimeout(5)

		location_message = "".join(["HTTP/1.1 200 OK\r\n", "ST: upnp:rootdevice\r\n", "USN: uuid:{uuid}::upnp:rootdevice\r\n", "Location: {location}\r\n", "Cache-Control: max-age=60\r\n\r\n"])

		class Request(BaseHTTPRequestHandler):

			def __init__(self, request_text):
				self.rfile = StringIO(request_text)
				self.raw_requestline = self.rfile.readline()
				self.error_code = self.error_message = None
				self.parse_request()

			def send_error(self, code, message=None):
				self.error_code = code
				self.error_message = message

		class Response(HTTPResponse):
			def __init__(self, response_text):
				self.fp = StringIO(response_text)
				self.debuglevel = 0
				self.strict = 0
				self.msg = None
				self._method = None
				self.begin()

		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
		sock.bind(('', 1900))

		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton('239.255.255.250') + socket.inet_aton('0.0.0.0'))

		self.logger.info("Registered {} for SSDP".format(INSTANCENAME))

		self._ssdp_notify(port, alive=True)

		try:
			while (True):
				try:
					data, address = sock.recvfrom(4096)
					request = Request(data)
					if not request.error_code and request.command == "M-SEARCH" and request.path == "*" and (request.headers["ST"] == "upnp:rootdevice" or request.headers["ST"] == "ssdp:all") and request.headers["MAN"] == '"ssdp:discover"':
						message = location_message.format(uuid=UUID, location="http://192.168.1.3:5000/plugin/discovery/discovery.xml")
						sock.sendto(message, address)
						self.logger.info("Sent M-SEARCH reply for {path} and {st} to {address!r}".format(path=request.path, st=request.headers["ST"], address=address))
				except socket.timeout:
					self._ssdp_notify(port, alive=True)
		finally:
			try:
				sock.close()
			except:
				pass


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

