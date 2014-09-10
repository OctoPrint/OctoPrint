# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"


import collections
import logging
import os
import flask

import octoprint.plugin
import octoprint.util

try:
	import pybonjour
except:
	pybonjour = False

default_settings = {
	"publicHost": None,
	"publicPort": None,
	"pathPrefix": None,
	"httpUsername": None,
	"httpPassword": None,
	"upnpUuid": None,
	"zeroConf": []
}
s = octoprint.plugin.plugin_settings("discovery", defaults=default_settings)


def get_uuid():
	upnpUuid = s.get(["upnpUuid"])
	if upnpUuid is None:
		import uuid
		upnpUuid = str(uuid.uuid4())
		s.set(["upnpUuid"], upnpUuid)
		s.save()
	return upnpUuid
UUID = get_uuid()
del get_uuid


def get_instance_name():
	name = s.globalGet(["appearance", "name"])
	if name:
		return "OctoPrint instance \"{}\"".format(name)
	else:
		import socket
		return "OctoPrint instance on {}".format(socket.gethostname())


blueprint = flask.Blueprint("plugin.discovery", __name__, template_folder=os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates"))

@blueprint.route("/discovery.xml")
def discovery():
	logging.getLogger("octoprint.plugins." + __name__).info("Rendering discovery.xml")
	response = flask.make_response(flask.render_template("discovery.jinja2",
	                             friendlyName=get_instance_name(),
	                             manufacturer="The OctoPrint project",
	                             manufacturerUrl="http://www.octoprint.org",
	                             modelName="OctoPrint",
	                             uuid=UUID,
	                             presentationUrl=flask.url_for("index", _external=True)))
	response.headers['Content-Type'] = 'application/xml'
	return response

class DiscoveryPlugin(octoprint.plugin.types.StartupPlugin,
                      octoprint.plugin.types.ShutdownPlugin,
                      octoprint.plugin.types.BlueprintPlugin,
                      octoprint.plugin.types.SettingsPlugin):
	def __init__(self):
		self.logger = logging.getLogger("octoprint.plugins." + __name__)

		self.host = None
		self.port = None

		# zeroconf
		self._sd_refs = {}

		# upnp/ssdp
		self._ssdp_monitor_active = False
		self._ssdp_monitor_thread = None
		self._ssdp_notify_timeout = 10
		self._ssdp_last_notify = 0

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
		public_host = s.get(["publicHost"])
		if public_host:
			host = public_host
		public_port = s.get(["publicPort"])
		if public_port:
			port = public_port

		self.host = host
		self.port = port

		# Zeroconf
		self.zeroconf_register("_http._tcp", get_instance_name(), txt_record=self._create_base_txt_record_dict())
		self.zeroconf_register("_octoprint._tcp", get_instance_name(), txt_record=self._create_octoprint_txt_record_dict())
		for zeroconf in s.get(["zeroConf"]):
			if "service" in zeroconf:
				self.zeroconf_register(
					zeroconf["service"],
					zeroconf["name"] if "name" in zeroconf else get_instance_name(),
					port=zeroconf["port"] if "port" in zeroconf else None,
					txt_record=zeroconf["txtRecord"] if "txtRecord" in zeroconf else None
				)

		# SSDP
		self._ssdp_register()

	#~~ ShutdownPlugin API

	def on_shutdown(self):
		self._ssdp_unregister()

	#~~ SettingsPlugin API

	def on_settings_load(self):
		return {
			"publicHost": s.get(["publicHost"]),
			"publicPort": s.getInt(["publicPort"]),
			"pathPrefix": s.get(["pathPrefix"]),
			"httpUsername": s.get(["httpUsername"]),
			"httpPassword": s.get(["httpPassword"])
		}

	def on_settings_save(self, data):
		if "publicHost" in data and data["publicHost"]:
			s.set(["publicHost"], data["publicHost"])
		if "publicPort" in data and data["publicPort"]:
			s.setInt(["publicPort"], data["publicPort"])
		if "pathPrefix" in data and data["pathPrefix"]:
			s.set(["pathPrefix"], data["pathPrefix"])
		if "httpUsername" in data and data["httpUsername"]:
			s.set(["httpUsername"], data["httpUsername"])
		if "httpPassword" in data and data["httpPassword"]:
			s.set(["httpPassword"], data["httpPassword"])

	#~~ internals

	# ZeroConf

	def zeroconf_register(self, service_type, name, port=None, txt_record=None):
		if not pybonjour:
			return

		def register_callback(sd_ref, flags, error_code, name, reg_type, domain):
			if error_code == pybonjour.kDNSServiceErr_NoError:
				self.logger.info("Registered {name} for {reg_type} with domain {domain}".format(**locals()))

		params = dict(
			name=name,
			regtype=service_type,
			port=port if port else self.port,
			callBack=register_callback
		)
		if txt_record:
			params["txtRecord"] = pybonjour.TXTRecord(txt_record)

		self._sd_refs[service_type] = pybonjour.DNSServiceRegister(**params)
		pybonjour.DNSServiceProcessResult(self._sd_refs[service_type])

	def zeroconf_browse(self, service_type, block=False, callback=None, timeout=5):
		if not pybonjour:
			return None

		import threading
		import time
		import select

		result = []
		result_available = threading.Event()
		result_available.clear()

		def resolve_callback(sd_ref, flags, interface_index, error_code, fullname, hosttarget, port, txt_record):
			if error_code == pybonjour.kDNSServiceErr_NoError:
				txt_record_dict = None
				if txt_record:
					record = pybonjour.TXTRecord.parse(txt_record)
					txt_record_dict = dict()
					for key, value in record:
						txt_record_dict[key] = value

				name = fullname[:fullname.find(service_type) - 1].replace("\\032", " ")
				host = hosttarget[:-1]

				self.logger.debug("Resolved a result for Zeroconf resolution of {service_type}: {name} @ {host}".format(service_type=service_type, name=name, host=host))
				result.append(dict(
					name=name,
					host=host,
					port=port,
					txt_record=txt_record_dict
				))

		def browse_callback(sd_ref, flags, interface_index, error_code, service_name, regtype, reply_domain):
			if error_code != pybonjour.kDNSServiceErr_NoError:
				return

			if not (flags & pybonjour.kDNSServiceFlagsAdd):
				return

			self.logger.debug("Got a browsing result for Zeroconf resolution of {service_type}, resolving...".format(service_type=service_type))
			resolve_ref = pybonjour.DNSServiceResolve(0, interface_index, service_name, regtype, reply_domain, resolve_callback)
			try:
				pybonjour.DNSServiceProcessResult(resolve_ref)
			finally:
				resolve_ref.close()

		self.logger.debug("Browsing Zeroconf for {service_type}".format(service_type=service_type))

		def browse():
			sd_ref = pybonjour.DNSServiceBrowse(regtype=service_type, callBack=browse_callback)
			start = time.time()
			try:
				while start + timeout > time.time():
					ready = select.select([sd_ref], [], [], timeout)
					if sd_ref in ready[0]:
						pybonjour.DNSServiceProcessResult(sd_ref)
			finally:
				sd_ref.close()

			if callback:
				callback(result)
			result_available.set()

		browse_thread = threading.Thread(target=browse)
		browse_thread.daemon = True
		browse_thread.start()

		if block:
			result_available.wait()
		return result

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

	# SSDP/UPNP

	def ssdp_browse(self, query, block=False, callback=None, timeout=1, retries=5):
		import threading

		import httplib
		import io
		class Response(httplib.HTTPResponse):
			def __init__(self, response_text):
				self.fp = io.BytesIO(response_text)
				self.debuglevel = 0
				self.strict = 0
				self.msg = None
				self._method = None
				self.begin()

		result = []
		result_available = threading.Event()
		result_available.clear()

		def browse():
			import socket

			socket.setdefaulttimeout(timeout)

			search_message = "".join([
				"M-SEARCH * HTTP/1.1\r\n",
				"ST: {query}\r\n",
				"MX: 3\r\n",
				"MAN: \"ssdp:discovery\"\r\n",
				"HOST: 239.255.255.250:1900\r\n\r\n"
			])

			for _ in xrange(retries):
				for addr in octoprint.util.interface_addresses():
					try:
						sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
						sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
						sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
						sock.bind((addr, 0))

						message = search_message.format(query=query)
						for _ in xrange(2):
							sock.sendto(message, ("239.255.255.250", 1900))

						try:
							data = sock.recv(1024)
						except socket.timeout:
							pass
						else:
							response = Response(data)

							result.append(response.getheader("Location"))
					except Exception as e:
						self.logger.exception("oops with {addr}".format(addr=addr))
						pass

			if callback:
				callback(result)
			result_available.set()

		browse_thread = threading.Thread(target=browse)
		browse_thread.daemon = True
		browse_thread.start()

		if block:
			result_available.wait()

		return result

	def _ssdp_register(self):
		import threading

		self._ssdp_monitor_active = True

		self._ssdp_monitor_thread = threading.Thread(target=self._ssdp_monitor, kwargs=dict(timeout=self._ssdp_notify_timeout))
		self._ssdp_monitor_thread.daemon = True
		self._ssdp_monitor_thread.start()

	def _ssdp_unregister(self):
		self._ssdp_monitor_active = False
		if self.host and self.port:
			for _ in xrange(2):
				self._ssdp_notify(alive=False)

	def _ssdp_notify(self, alive=True):
		import socket
		import time

		if self._ssdp_last_notify + self._ssdp_notify_timeout > time.time():
			return

		if alive and not self._ssdp_monitor_active:
			return

		for addr in octoprint.util.interface_addresses():
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
				sock.bind((addr, 0))

				location = "http://{addr}:{port}/plugin/discovery/discovery.xml".format(addr=addr, port=self.port)

				self.logger.debug("Sending NOTIFY {} via {}".format("alive" if alive else "byebye", addr))
				notify_message = "".join([
					"NOTIFY * HTTP/1.1\r\n",
					"Server: Python/2.7\r\n",
					"Cache-Control: max-age=900\r\n",
					"Location: {location}\r\n",
					"NTS: {nts}\r\n",
					"NT: upnp:rootdevice\r\n",
					"USN: uuid:{uuid}::upnp:rootdevice\r\n",
					"Host: 239.255.255.250:1900\r\n\r\n"
				])
				message = notify_message.format(uuid=UUID, location=location, nts="ssdp:alive" if alive else "ssdp:byebye")
				for _ in xrange(2):
					sock.sendto(message, ("239.255.255.250", 1900))
			except Exception as e:
				pass

		self._ssdp_last_notify = time.time()

	def _ssdp_monitor(self, timeout=5):

		from BaseHTTPServer import BaseHTTPRequestHandler
		from StringIO import StringIO
		import socket

		socket.setdefaulttimeout(timeout)

		location_message = "".join([
			"HTTP/1.1 200 OK\r\n",
			"ST: upnp:rootdevice\r\n",
			"USN: uuid:{uuid}::upnp:rootdevice\r\n",
			"Location: {location}\r\n",
			"Cache-Control: max-age=60\r\n\r\n"
		])

		class Request(BaseHTTPRequestHandler):

			def __init__(self, request_text):
				self.rfile = StringIO(request_text)
				self.raw_requestline = self.rfile.readline()
				self.error_code = self.error_message = None
				self.parse_request()

			def send_error(self, code, message=None):
				self.error_code = code
				self.error_message = message

		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
		sock.bind(('', 1900))

		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton('239.255.255.250') + socket.inet_aton('0.0.0.0'))

		self.logger.info("Registered {} for SSDP".format(get_instance_name()))

		self._ssdp_notify(alive=True)

		try:
			while (self._ssdp_monitor_active):
				try:
					data, address = sock.recvfrom(4096)
					request = Request(data)
					if not request.error_code and request.command == "M-SEARCH" and request.path == "*" and (request.headers["ST"] == "upnp:rootdevice" or request.headers["ST"] == "ssdp:all") and request.headers["MAN"] == '"ssdp:discover"':
						interface_address = octoprint.util.address_for_client(*address)
						if not interface_address:
							self.logger.warn("Can't determine address to user for client {}, not sending a M-SEARCH reply".format(address))
							continue
						message = location_message.format(uuid=UUID, location="http://{host}:{port}/plugin/discovery/discovery.xml".format(host=interface_address, port=self.port))
						sock.sendto(message, address)
						self.logger.debug("Sent M-SEARCH reply for {path} and {st} to {address!r}".format(path=request.path, st=request.headers["ST"], address=address))
				except socket.timeout:
					pass
				finally:
					self._ssdp_notify(alive=True)
		finally:
			try:
				sock.close()
			except:
				pass


__plugin_name__ = "Discovery"
__plugin_version__ = "0.1"
__plugin_description__ = "Makes the OctoPrint instance discoverable via Bonjour/Avahi/Zeroconf and uPnP"

def __plugin_check__():
	if not pybonjour:
		# no pybonjour available, we can't continue
		logging.getLogger("octoprint.plugins." + __name__).info("pybonjour is not installed, Zeroconf Discovery won't be available")

	discovery_plugin = DiscoveryPlugin()

	global __plugin_implementations__
	__plugin_implementations__ = [discovery_plugin]

	global __plugin_helpers__
	__plugin_helpers__ = dict(
		ssdp_browse=discovery_plugin.ssdp_browse
	)
	if pybonjour:
		__plugin_helpers__["zeroconf_browse"] = discovery_plugin.zeroconf_browse

	return True

