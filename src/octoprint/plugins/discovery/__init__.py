# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

"""
The SSDP/UPNP implementations has been largely inspired by https://gist.github.com/schlamar/2428250
"""

import logging
import os
import flask

import octoprint.plugin
import octoprint.util

try:
	import pybonjour
except:
	pybonjour = False


__plugin_name__ = "Discovery"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "https://github.com/foosel/OctoPrint/wiki/Plugin:-Discovery"
__plugin_description__ = "Makes the OctoPrint instance discoverable via Bonjour/Avahi/Zeroconf and uPnP"
__plugin_license__ = "AGPLv3"

def __plugin_init__():
	if not pybonjour:
		# no pybonjour available, we can't use that
		logging.getLogger("octoprint.plugins." + __name__).info("pybonjour is not installed, Zeroconf Discovery won't be available")

	discovery_plugin = DiscoveryPlugin()

	global __plugin_implementations__
	__plugin_implementations__ = [discovery_plugin]

	global __plugin_helpers__
	__plugin_helpers__ = dict(
		ssdp_browse=discovery_plugin.ssdp_browse
	)
	if pybonjour:
		__plugin_helpers__.update(dict(
			zeroconf_browse=discovery_plugin.zeroconf_browse,
			zeroconf_register=discovery_plugin.zeroconf_register,
			zeroconf_unregister=discovery_plugin.zeroconf_unregister
		))

class DiscoveryPlugin(octoprint.plugin.StartupPlugin,
                      octoprint.plugin.ShutdownPlugin,
                      octoprint.plugin.BlueprintPlugin,
                      octoprint.plugin.SettingsPlugin):

	ssdp_multicast_addr = "239.255.255.250"

	ssdp_multicast_port = 1900

	def __init__(self):
		self.host = None
		self.port = None

		# zeroconf
		self._sd_refs = dict()
		self._cnames = dict()

		# upnp/ssdp
		self._ssdp_monitor_active = False
		self._ssdp_monitor_thread = None
		self._ssdp_notify_timeout = 10
		self._ssdp_last_notify = 0

	##~~ SettingsPlugin API

	def get_settings_defaults(self):
		return {
			"publicHost": None,
			"publicPort": None,
			"pathPrefix": None,
			"httpUsername": None,
			"httpPassword": None,
			"upnpUuid": None,
			"zeroConf": [],
			"model": {
				"name": None,
				"description": None,
				"number": None,
				"url": None,
				"serial": None,
				"vendor": None,
				"vendorUrl": None
			}
		}

	##~~ BlueprintPlugin API -- used for providing the SSDP device descriptor XML

	@octoprint.plugin.BlueprintPlugin.route("/discovery.xml", methods=["GET"])
	def discovery(self):
		self._logger.debug("Rendering discovery.xml")

		modelName = self._settings.get(["model", "name"])
		if not modelName:
			import octoprint.server
			modelName = octoprint.server.DISPLAY_VERSION

		vendor = self._settings.get(["model", "vendor"])
		vendorUrl = self._settings.get(["model", "vendorUrl"])
		if not vendor:
			vendor = "The OctoPrint Project"
			vendorUrl = "http://www.octoprint.org/"

		response = flask.make_response(flask.render_template("discovery.xml.jinja2",
		                                                     friendlyName=self.get_instance_name(),
		                                                     manufacturer=vendor,
		                                                     manufacturerUrl=vendorUrl,
		                                                     modelName=modelName,
		                                                     modelDescription=self._settings.get(["model", "description"]),
		                                                     modelNumber=self._settings.get(["model", "number"]),
		                                                     modelUrl=self._settings.get(["model", "url"]),
		                                                     serialNumber=self._settings.get(["model", "serial"]),
		                                                     uuid=self.get_uuid(),
		                                                     presentationUrl=flask.url_for("index", _external=True)))
		response.headers['Content-Type'] = 'application/xml'
		return response

	def is_blueprint_protected(self):
		return False

	##~~ StartupPlugin API -- used for registering OctoPrint's Zeroconf and SSDP services upon application startup

	def on_startup(self, host, port):
		public_host = self._settings.get(["publicHost"])
		if public_host:
			host = public_host
		public_port = self._settings.get(["publicPort"])
		if public_port:
			port = public_port

		self.host = host
		self.port = port

		# Zeroconf
		self.zeroconf_register("_http._tcp", self.get_instance_name(), txt_record=self._create_http_txt_record_dict())
		self.zeroconf_register("_octoprint._tcp", self.get_instance_name(), txt_record=self._create_octoprint_txt_record_dict())
		for zeroconf in self._settings.get(["zeroConf"]):
			if "service" in zeroconf:
				self.zeroconf_register(
					zeroconf["service"],
					zeroconf["name"] if "name" in zeroconf else self.get_instance_name(),
					port=zeroconf["port"] if "port" in zeroconf else None,
					txt_record=zeroconf["txtRecord"] if "txtRecord" in zeroconf else None
				)

		# SSDP
		self._ssdp_register()

	##~~ ShutdownPlugin API -- used for unregistering OctoPrint's Zeroconf and SSDP service upon application shutdown

	def on_shutdown(self):
		for key in self._sd_refs:
			reg_type, port = key
			self.zeroconf_unregister(reg_type, port)

		self._ssdp_unregister()

	##~~ helpers

	# ZeroConf

	def zeroconf_register(self, reg_type, name=None, port=None, txt_record=None):
		"""
		Registers a new service with Zeroconf/Bonjour/Avahi.

		:param reg_type: type of service to register, e.g. "_gntp._tcp"
		:param name: displayable name of the service, if not given defaults to the OctoPrint instance name
		:param port: port to register for the service, if not given defaults to OctoPrint's (public) port
		:param txt_record: optional txt record to attach to the service, dictionary of key-value-pairs
		"""

		if not pybonjour:
			return

		if not name:
			name = self.get_instance_name()
		if not port:
			port = self.port

		params = dict(
			name=name,
			regtype=reg_type,
			port=port
		)
		if txt_record:
			params["txtRecord"] = pybonjour.TXTRecord(txt_record)

		key = (reg_type, port)
		self._sd_refs[key] = pybonjour.DNSServiceRegister(**params)
		self._logger.info(u"Registered {name} for {reg_type}".format(**locals()))

	def zeroconf_unregister(self, reg_type, port=None):
		"""
		Unregisteres a previously registered Zeroconf/Bonjour/Avahi service identified by service and port.

		:param reg_type: the type of the service to be unregistered
		:param port: the port of the service to be unregistered, defaults to OctoPrint's (public) port if not given
		:return:
		"""

		if not pybonjour:
			return

		if not port:
			port = self.port

		key = (reg_type, port)
		if not key in self._sd_refs:
			return

		sd_ref = self._sd_refs[key]
		try:
			sd_ref.close()
			self._logger.debug("Unregistered {reg_type} on port {port}".format(reg_type=reg_type, port=port))
		except:
			self._logger.exception("Could not unregister {reg_type} on port {port}".format(reg_type=reg_type, port=port))

	def zeroconf_browse(self, service_type, block=True, callback=None, browse_timeout=5, resolve_timeout=5):
		"""
		Browses for services on the local network providing the specified service type. Can be used either blocking or
		non-blocking.

		The non-blocking version (default behaviour) will not return until the lookup has completed and
		return all results that were found.

		For non-blocking version, set `block` to `False` and provide a `callback` to be called once the lookup completes.
		If no callback is provided in non-blocking mode, a ValueError will be raised.

		The results are provided as a list of discovered services, with each service being described by a dictionary
		with the following keys:

		  * `name`: display name of the service
		  * `host`: host name of the service
		  * `post`: port the service is listening on
		  * `txt_record`: TXT record of the service as a dictionary, exact contents depend on the service

		Callbacks will be called with that list as the single parameter supplied to them. Thus, the following is an
		example for a valid callback:

		    def browse_callback(results):
		      for result in results:
		        print "Name: {name}, Host: {host}, Port: {port}, TXT: {txt_record!r}".format(**result)

		:param service_type: the service type to browse for
		:param block: whether to block, defaults to True
		:param callback: callback to call once lookup has completed, must be set when `block` is set to `False`
		:param browse_timeout: timeout for browsing operation
		:param resolve_timeout: timeout for resolving operations for discovered records
		:return: if `block` is `True` a list of the discovered services, an empty list otherwise (results will then be
		         supplied to the callback instead)
		"""

		if not pybonjour:
			return None

		import threading
		import select

		if not block and not callback:
			raise ValueError("Non-blocking mode but no callback given")

		result = []
		result_available = threading.Event()
		result_available.clear()

		resolved = []

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

				self._logger.debug("Resolved a result for Zeroconf resolution of {service_type}: {name} @ {host}".format(service_type=service_type, name=name, host=host))
				result.append(dict(
					name=name,
					host=host,
					port=port,
					txt_record=txt_record_dict
				))
				resolved.append(True)

		def browse_callback(sd_ref, flags, interface_index, error_code, service_name, regtype, reply_domain):
			if error_code != pybonjour.kDNSServiceErr_NoError:
				return

			if not (flags & pybonjour.kDNSServiceFlagsAdd):
				return

			self._logger.debug("Got a browsing result for Zeroconf resolution of {service_type}, resolving...".format(service_type=service_type))
			resolve_ref = pybonjour.DNSServiceResolve(0, interface_index, service_name, regtype, reply_domain, resolve_callback)

			try:
				while not resolved:
					ready = select.select([resolve_ref], [], [], resolve_timeout)
					if resolve_ref not in ready[0]:
						break

					pybonjour.DNSServiceProcessResult(resolve_ref)
				else:
					resolved.pop()
			finally:
				resolve_ref.close()

		self._logger.debug("Browsing Zeroconf for {service_type}".format(service_type=service_type))

		def browse():
			sd_ref = pybonjour.DNSServiceBrowse(regtype=service_type, callBack=browse_callback)
			try:
				while True:
					ready = select.select([sd_ref], [], [], browse_timeout)

					if not ready[0]:
						break

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
		else:
			return []

	# SSDP/UPNP

	def ssdp_browse(self, query, block=True, callback=None, timeout=1, retries=5):
		"""
		Browses for UPNP services matching the supplied query. Can be used either blocking or
		non-blocking.

		The non-blocking version (default behaviour) will not return until the lookup has completed and
		return all results that were found.

		For non-blocking version, set `block` to `False` and provide a `callback` to be called once the lookup completes.
		If no callback is provided in non-blocking mode, a ValueError will be raised.

		The results are provided as a list of discovered locations of device descriptor files.

		Callbacks will be called with that list as the single parameter supplied to them. Thus, the following is an
		example for a valid callback:

		    def browse_callback(results):
		      for result in results:
		        print "Location: {}".format(result)

		:param query: the SSDP query to send, e.g. "upnp:rootdevice" to search for all devices
		:param block: whether to block, defaults to True
		:param callback: callback to call in non-blocking mode when lookup has finished, must be set if block is False
		:param timeout: timeout in seconds to wait for replies to the M-SEARCH query per interface, defaults to 1
		:param retries: number of retries to perform the lookup on all interfaces, defaults to 5
		:return: if `block` is `True` a list of the discovered devices, an empty list otherwise (results will then be
		         supplied to the callback instead)
		"""

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
				"HOST: {mcast_addr}:{mcast_port}\r\n\r\n"
			])

			for _ in xrange(retries):
				for addr in octoprint.util.interface_addresses():
					try:
						sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
						sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
						sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
						sock.bind((addr, 0))

						message = search_message.format(query=query,
						                                mcast_addr=self.__class__.ssdp_multicast_addr,
						                                mcast_port=self.__class__.ssdp_multicast_port)
						for _ in xrange(2):
							sock.sendto(message, (self.__class__.ssdp_multicast_addr, self.__class__.ssdp_multicast_port))

						try:
							data = sock.recv(1024)
						except socket.timeout:
							pass
						else:
							response = Response(data)

							result.append(response.getheader("Location"))
					except:
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
		else:
			return []

	##~~ internals

	# Zeroconf

	def _create_http_txt_record_dict(self):
		"""
		Creates a TXT record for the _http._tcp Zeroconf service supplied by this OctoPrint instance.

		Defines the keys for _http._tcp as defined in http://www.dns-sd.org/txtrecords.html

		:return: a dictionary containing the defined key-value-pairs, ready to be turned into a TXT record
		"""

		# determine path entry
		path = "/"
		if self._settings.get(["pathPrefix"]):
			path = self._settings.get(["pathPrefix"])
		else:
			prefix = self._settings.global_get(["server", "reverseProxy", "prefixFallback"])
			if prefix:
				path = prefix

		# fetch username and password (if set)
		username = self._settings.get(["httpUsername"])
		password = self._settings.get(["httpPassword"])

		entries = dict(
			path=path
		)

		if username and password:
			entries.update(dict(u=username, p=password))

		return entries

	def _create_octoprint_txt_record_dict(self):
		"""
		Creates a TXT record for the _octoprint._tcp Zeroconf service supplied by this OctoPrint instance.

		The following keys are defined:

		  * `path`: path prefix to actual OctoPrint instance, inherited from _http._tcp
		  * `u`: username if HTTP Basic Auth is used, optional, inherited from _http._tcp
		  * `p`: password if HTTP Basic Auth is used, optional, inherited from _http._tcp
		  * `version`: OctoPrint software version
		  * `api`: OctoPrint API version
		  * `model`: Model of the device that is running OctoPrint
		  * `vendor`: Vendor of the device that is running OctoPrint

		:return: a dictionary containing the defined key-value-pairs, ready to be turned into a TXT record
		"""

		entries = self._create_http_txt_record_dict()

		import octoprint.server
		import octoprint.server.api

		entries.update(dict(
			version=octoprint.server.VERSION,
			api=octoprint.server.api.VERSION,
			))

		modelName = self._settings.get(["model", "name"])
		if modelName:
			entries.update(dict(model=modelName))
		vendor = self._settings.get(["model", "vendor"])
		if vendor:
			entries.update(dict(vendor=vendor))

		return entries

	# SSDP/UPNP

	def _ssdp_register(self):
		"""
		Registers the OctoPrint instance as basic service with a presentation URL pointing to the web interface
		"""

		import threading

		self._ssdp_monitor_active = True

		self._ssdp_monitor_thread = threading.Thread(target=self._ssdp_monitor, kwargs=dict(timeout=self._ssdp_notify_timeout))
		self._ssdp_monitor_thread.daemon = True
		self._ssdp_monitor_thread.start()

	def _ssdp_unregister(self):
		"""
		Unregisters the OctoPrint instance again
		"""

		self._ssdp_monitor_active = False
		if self.host and self.port:
			for _ in xrange(2):
				self._ssdp_notify(alive=False)

	def _ssdp_notify(self, alive=True):
		"""
		Sends an SSDP notify message across the connected networks.

		:param alive: True to send an "ssdp:alive" message, False to send an "ssdp:byebye" message
		"""

		import socket
		import time

		if alive and self._ssdp_last_notify + self._ssdp_notify_timeout > time.time():
			# we just sent an alive, no need to send another one now
			return

		if alive and not self._ssdp_monitor_active:
			# the monitor already shut down, alive messages don't make sense anymore as byebye will shortly follow
			return

		for addr in octoprint.util.interface_addresses():
			try:
				sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
				sock.bind((addr, 0))

				location = "http://{addr}:{port}/plugin/discovery/discovery.xml".format(addr=addr, port=self.port)

				self._logger.debug("Sending NOTIFY {} via {}".format("alive" if alive else "byebye", addr))
				notify_message = "".join([
					"NOTIFY * HTTP/1.1\r\n",
					"Server: Python/2.7\r\n",
					"Cache-Control: max-age=900\r\n",
					"Location: {location}\r\n",
					"NTS: {nts}\r\n",
					"NT: upnp:rootdevice\r\n",
					"USN: uuid:{uuid}::upnp:rootdevice\r\n",
					"HOST: {mcast_addr}:{mcast_port}\r\n\r\n"
				])
				message = notify_message.format(uuid=self.get_uuid(),
				                                location=location,
				                                nts="ssdp:alive" if alive else "ssdp:byebye",
				                                mcast_addr=self.__class__.ssdp_multicast_addr,
				                                mcast_port=self.__class__.ssdp_multicast_port)
				for _ in xrange(2):
					# send twice, stuff might get lost, it's only UDP
					sock.sendto(message, (self.__class__.ssdp_multicast_addr, self.__class__.ssdp_multicast_port))
			except:
				pass

		self._ssdp_last_notify = time.time()

	def _ssdp_monitor(self, timeout=5):
		"""
		Monitor thread that listens on the multicast address for M-SEARCH requests and answers them if they are relevant

		:param timeout: timeout after which to stop waiting for M-SEARCHs for a short while in order to put out an
		                alive message
		"""

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
		sock.bind(('', self.__class__.ssdp_multicast_port))

		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.__class__.ssdp_multicast_addr) + socket.inet_aton('0.0.0.0'))

		self._logger.info(u"Registered {} for SSDP".format(self.get_instance_name()))

		self._ssdp_notify(alive=True)

		try:
			while (self._ssdp_monitor_active):
				try:
					data, address = sock.recvfrom(4096)
					request = Request(data)
					if not request.error_code and request.command == "M-SEARCH" and request.path == "*" and (request.headers["ST"] == "upnp:rootdevice" or request.headers["ST"] == "ssdp:all") and request.headers["MAN"] == '"ssdp:discover"':
						interface_address = octoprint.util.address_for_client(*address)
						if not interface_address:
							self._logger.warn("Can't determine address to user for client {}, not sending a M-SEARCH reply".format(address))
							continue
						message = location_message.format(uuid=self.get_uuid(), location="http://{host}:{port}/plugin/discovery/discovery.xml".format(host=interface_address, port=self.port))
						sock.sendto(message, address)
						self._logger.debug("Sent M-SEARCH reply for {path} and {st} to {address!r}".format(path=request.path, st=request.headers["ST"], address=address))
				except socket.timeout:
					pass
				finally:
					self._ssdp_notify(alive=True)
		finally:
			try:
				sock.close()
			except:
				pass

	##~~ helpers

	def get_uuid(self):
		upnpUuid = self._settings.get(["upnpUuid"])
		if upnpUuid is None:
			import uuid
			upnpUuid = str(uuid.uuid4())
			self._settings.set(["upnpUuid"], upnpUuid)
			self._settings.save()
		return upnpUuid

	def get_instance_name(self):
		name = self._settings.global_get(["appearance", "name"])
		if name:
			return u"OctoPrint instance \"{}\"".format(name)
		else:
			import socket
			return u"OctoPrint instance on {}".format(socket.gethostname())
