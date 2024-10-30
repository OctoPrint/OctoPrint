__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

"""
The SSDP/UPNP implementations has been largely inspired by https://gist.github.com/schlamar/2428250

For a spec see http://www.upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.0.pdf
"""

import collections
import platform
import socket
import time

import flask
import zeroconf
from flask_babel import gettext

import octoprint.plugin
import octoprint.util


def __plugin_load__():
    plugin = DiscoveryPlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_helpers__
    __plugin_helpers__ = {
        "ssdp_browse": plugin.ssdp_browse,
        "zeroconf_browse": plugin.zeroconf_browse,
        "zeroconf_register": plugin.zeroconf_register,
        "zeroconf_unregister": plugin.zeroconf_unregister,
    }


class DiscoveryPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.SettingsPlugin,
):
    ssdp_multicast_addr = "239.255.255.250"  # IPv6: ff0X::c

    ssdp_multicast_port = 1900

    ssdp_server = "{}/{} UPnP/1.0 OctoPrint/{}".format(
        platform.system(), platform.version(), octoprint.__version__
    )

    # noinspection PyMissingConstructor
    def __init__(self):
        self.host = None
        self.port = None

        # zeroconf
        self._zeroconf = None
        self._zeroconf_registrations = collections.defaultdict(list)

        # upnp/ssdp
        self._ssdp_monitor_active = False
        self._ssdp_monitor_thread = None
        self._ssdp_notify_timeout = 30
        self._ssdp_last_notify = 0

    def initialize(self):
        self._zeroconf = zeroconf.Zeroconf(interfaces=self.get_interface_addresses())

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
                "vendorUrl": None,
            },
            "addresses": None,
            "ignoredAddresses": None,
            "interfaces": None,
            "ignoredInterfaces": None,
        }

    ##~~ BlueprintPlugin API -- used for providing the SSDP device descriptor XML

    @octoprint.plugin.BlueprintPlugin.route("/discovery.xml", methods=["GET"])
    def discovery(self):
        self._logger.debug("Rendering discovery.xml")

        vendor = self._settings.get(["model", "vendor"])
        if not vendor:
            vendor = "The OctoPrint Project"

        vendorUrl = self._settings.get(["model", "vendorUrl"])
        if not vendorUrl:
            vendorUrl = "https://octoprint.org/"

        response = flask.make_response(
            flask.render_template(
                "discovery.xml.jinja2",
                friendlyName=self.get_instance_name(),
                manufacturer=vendor,
                manufacturerUrl=vendorUrl,
                modelName=self._settings.get(["model", "name"]),
                modelDescription=self._settings.get(["model", "description"]),
                modelNumber=self._settings.get(["model", "number"]),
                modelUrl=self._settings.get(["model", "url"]),
                serialNumber=self._settings.get(["model", "serial"]),
                uuid=self.get_uuid(),
                presentationUrl=flask.url_for("index", _external=True),
            )
        )
        response.headers["Content-Type"] = "application/xml"
        return response

    def is_blueprint_protected(self):
        return False

    def is_blueprint_csrf_protected(self):
        return True

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
        instance_name = self.get_instance_name()
        self.zeroconf_register(
            "_http._tcp", instance_name, txt_record=self._create_http_txt_record_dict()
        )
        self.zeroconf_register(
            "_octoprint._tcp",
            instance_name,
            txt_record=self._create_octoprint_txt_record_dict(),
        )
        for zc in self._settings.get(["zeroConf"]):
            if "service" in zc:
                self.zeroconf_register(
                    zc["service"],
                    zc.get("name", instance_name),
                    port=zc.get("port"),
                    txt_record=zc.get("txtRecord"),
                )

        # SSDP
        self._ssdp_register()

    ##~~ ShutdownPlugin API -- used for unregistering OctoPrint's Zeroconf and SSDP service upon application shutdown

    def on_shutdown(self):
        registrations = list(self._zeroconf_registrations.keys())
        for key in registrations:
            reg_type, port = key
            self.zeroconf_unregister(reg_type, port)

        self._ssdp_unregister()

    ##~~ helpers

    # ZeroConf

    def _format_zeroconf_service_type(self, service_type):
        if not service_type.endswith("."):
            service_type += "."
        if not service_type.endswith("local."):
            service_type += "local."
        return service_type

    def _format_zeroconf_name(self, name, service_type):
        service_type = self._format_zeroconf_service_type(service_type)
        return f"{name}.{service_type}"

    def _format_zeroconf_txt(self, record):
        result = {}
        if not record:
            return result

        for key, value in record.items():
            result[octoprint.util.to_bytes(key)] = octoprint.util.to_bytes(value)
        return result

    def zeroconf_register(self, reg_type, name=None, port=None, txt_record=None):
        """
        Registers a new service with Zeroconf/Bonjour/Avahi.

        :param reg_type: type of service to register, e.g. "_gntp._tcp"
        :param name: displayable name of the service, if not given defaults to the OctoPrint instance name
        :param port: port to register for the service, if not given defaults to OctoPrint's (public) port
        :param txt_record: optional txt record to attach to the service, dictionary of key-value-pairs
        """

        if not name:
            name = self.get_instance_name()
        if not port:
            port = self.port

        reg_type = self._format_zeroconf_service_type(reg_type)
        name = self._format_zeroconf_name(name, reg_type)
        txt_record = self._format_zeroconf_txt(txt_record)

        key = (reg_type, port)
        addresses = list(
            map(lambda x: socket.inet_aton(x), self.get_interface_addresses())
        )

        try:
            info = zeroconf.ServiceInfo(
                reg_type,
                name,
                addresses=addresses,
                port=port,
                server=f"{socket.gethostname()}.local.",
                properties=txt_record,
            )
            self._zeroconf.register_service(info, allow_name_change=True)
            self._zeroconf_registrations[key].append(info)
            self._logger.info(f"Registered '{name}' for {reg_type}")
        except Exception:
            self._logger.exception(
                f"Could not register {name} for {reg_type} on port {port}"
            )

    def zeroconf_unregister(self, reg_type, port=None):
        """
        Unregisters a previously registered Zeroconf/Bonjour/Avahi service identified by service and port.

        :param reg_type: the type of the service to be unregistered
        :param port: the port of the service to be unregistered, defaults to OctoPrint's (public) port if not given
        :return:
        """

        if not port:
            port = self.port
        reg_type = self._format_zeroconf_service_type(reg_type)

        key = (reg_type, port)
        if key not in self._zeroconf_registrations:
            return

        infos = self._zeroconf_registrations.pop(key)
        try:
            for info in infos:
                self._zeroconf.unregister_service(info)
            self._logger.debug(f"Unregistered {reg_type} on port {port}")
        except Exception:
            self._logger.exception(
                f"Could not (fully) unregister {reg_type} on port {port}"
            )

    def zeroconf_browse(
        self, service_type, block=True, callback=None, browse_timeout=5, resolve_timeout=5
    ):
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

        import threading

        if not block and not callback:
            raise ValueError("Non-blocking mode but no callback given")

        service_type = self._format_zeroconf_service_type(service_type)

        result = []
        result_available = threading.Event()
        result_available.clear()

        class ZeroconfListener:
            def __init__(self, logger):
                self._logger = logger

            def add_service(self, zeroconf, type, name):
                self._logger.debug(
                    "Got a browsing result for Zeroconf resolution of {}, resolving...".format(
                        type
                    )
                )
                info = zeroconf.get_service_info(
                    type, name, timeout=resolve_timeout * 1000
                )
                if info:

                    def to_result(info, address):
                        n = info.name[: -(len(type) + 1)]
                        p = info.port

                        self._logger.debug(
                            "Resolved a result for Zeroconf resolution of {}: {} @ {}:{}".format(
                                type, n, address, p
                            )
                        )

                        return {
                            "name": n,
                            "host": address,
                            "port": p,
                            "txt_record": info.properties,
                        }

                    for address in map(lambda x: socket.inet_ntoa(x), info.addresses):
                        result.append(to_result(info, address))

        self._logger.debug(f"Browsing Zeroconf for {service_type}")

        def browse():
            listener = ZeroconfListener(self._logger)
            browser = zeroconf.ServiceBrowser(self._zeroconf, service_type, listener)
            time.sleep(browse_timeout)
            browser.cancel()

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
                print("Location: {}".format(result))

        :param query: the SSDP query to send, e.g. "upnp:rootdevice" to search for all devices
        :param block: whether to block, defaults to True
        :param callback: callback to call in non-blocking mode when lookup has finished, must be set if block is False
        :param timeout: timeout in seconds to wait for replies to the M-SEARCH query per interface, defaults to 1
        :param retries: number of retries to perform the lookup on all interfaces, defaults to 5
        :return: if `block` is `True` a list of the discovered devices, an empty list otherwise (results will then be
                 supplied to the callback instead)
        """

        import io
        import threading
        from http.client import HTTPResponse

        class Response(HTTPResponse):
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
            socket.setdefaulttimeout(timeout)

            search_message = "".join(
                [
                    "M-SEARCH * HTTP/1.1\r\n",
                    "ST: {query}\r\n",
                    "MX: 3\r\n",
                    'MAN: "ssdp:discovery"\r\n',
                    "HOST: {mcast_addr}:{mcast_port}\r\n\r\n",
                ]
            )

            for _ in range(retries):
                for addr in self.get_interface_addresses():
                    try:
                        sock = socket.socket(
                            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
                        )
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                        sock.bind((addr, 0))

                        message = search_message.format(
                            query=query,
                            mcast_addr=self.__class__.ssdp_multicast_addr,
                            mcast_port=self.__class__.ssdp_multicast_port,
                        )
                        for _ in range(2):
                            sock.sendto(
                                message.encode("utf-8"),
                                (
                                    self.__class__.ssdp_multicast_addr,
                                    self.__class__.ssdp_multicast_port,
                                ),
                            )

                        try:
                            data = sock.recv(1024)
                        except socket.timeout:
                            pass
                        else:
                            response = Response(data)

                            result.append(response.getheader("Location"))
                    except Exception:
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
            prefix = self._settings.global_get(
                ["server", "reverseProxy", "prefixFallback"]
            )
            if prefix:
                path = prefix

        # fetch username and password (if set)
        username = self._settings.get(["httpUsername"])
        password = self._settings.get(["httpPassword"])

        entries = {"path": path}

        if username and password:
            entries.update({"u": username, "p": password})

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
        import octoprint.server
        import octoprint.server.api

        entries = self._create_http_txt_record_dict()
        entries.update(
            # This *should* be staying in the local network and thus not leak this info outside. If the
            # network is configured differently, we can consider this either a mistake, or an
            # explicit decision.
            version=octoprint.server.VERSION,
            api=octoprint.server.api.VERSION,
            uuid=self.get_uuid(),
        )

        modelName = self._settings.get(["model", "name"])
        if modelName:
            entries.update(model=modelName)
        vendor = self._settings.get(["model", "vendor"])
        if vendor:
            entries.update(vendor=vendor)

        return entries

    # SSDP/UPNP

    def _ssdp_register(self):
        """
        Registers the OctoPrint instance as basic service with a presentation URL pointing to the web interface
        """

        import threading

        self._ssdp_monitor_active = True

        self._ssdp_monitor_thread = threading.Thread(
            target=self._ssdp_monitor, kwargs={"timeout": self._ssdp_notify_timeout}
        )
        self._ssdp_monitor_thread.daemon = True
        self._ssdp_monitor_thread.start()

    def _ssdp_unregister(self):
        """
        Unregisters the OctoPrint instance again
        """

        self._ssdp_monitor_active = False
        if self.host and self.port:
            for _ in range(2):
                self._ssdp_notify(alive=False)

    def _ssdp_notify(self, alive=True):
        """
        Sends an SSDP notify message across the connected networks.

        :param alive: True to send an "ssdp:alive" message, False to send an "ssdp:byebye" message
        """

        if (
            alive
            and self._ssdp_last_notify + self._ssdp_notify_timeout > time.monotonic()
        ):
            # we just sent an alive, no need to send another one now
            return

        if alive and not self._ssdp_monitor_active:
            # the monitor already shut down, alive messages don't make sense anymore as byebye will shortly follow
            return

        for addr in self.get_interface_addresses():
            try:
                sock = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
                )
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
                sock.bind((addr, 0))

                location = "http://{addr}:{port}/plugin/discovery/discovery.xml".format(
                    addr=addr, port=self.port
                )

                self._logger.debug(
                    "Sending NOTIFY {} via {}".format(
                        "alive" if alive else "byebye", addr
                    )
                )
                notify_message = "".join(
                    [
                        "NOTIFY * HTTP/1.1\r\n",
                        "Server: {server}\r\n",
                        "Cache-Control: max-age=900\r\n",
                        "Location: {location}\r\n",
                        "NTS: {nts}\r\n",
                        "NT: {nt}\r\n",
                        "USN: {usn}\r\n",
                        "HOST: {mcast_addr}:{mcast_port}\r\n\r\n",
                    ]
                )
                uuid = self.get_uuid()
                for nt, usn in (
                    ("upnp:rootdevice", "uuid:{uuid}::upnp:rootdevice"),
                    ("uuid:{}", "uuid:{uuid}"),
                    (
                        "urn:schemas-upnp-org:device:basic:1",
                        "uuid:{uuid}::url:schemas-upnp-org:device:basic:1",
                    ),
                ):
                    message = notify_message.format(
                        uuid=uuid,
                        location=location,
                        nts="ssdp:alive" if alive else "ssdp:byebye",
                        nt=nt.format(uuid=uuid),
                        usn=usn.format(uuid=uuid),
                        server=self.ssdp_server,
                        mcast_addr=self.ssdp_multicast_addr,
                        mcast_port=self.ssdp_multicast_port,
                    )
                    for _ in range(2):
                        # send twice, stuff might get lost, it's only UDP
                        sock.sendto(
                            message.encode("utf-8"),
                            (self.ssdp_multicast_addr, self.ssdp_multicast_port),
                        )
            except Exception:
                pass

        self._ssdp_last_notify = time.monotonic()

    def _ssdp_monitor(self, timeout=5):
        """
        Monitor thread that listens on the multicast address for M-SEARCH requests and answers them if they are relevant

        :param timeout: timeout after which to stop waiting for M-SEARCHs for a short while in order to put out an
                        alive message
        """

        from http.server import BaseHTTPRequestHandler
        from io import BytesIO

        socket.setdefaulttimeout(timeout)

        location_message = "".join(
            [
                "HTTP/1.1 200 OK\r\n",
                "ST: upnp:rootdevice\r\n",
                "USN: uuid:{uuid}::upnp:rootdevice\r\n",
                "Location: {location}\r\n",
                "Cache-Control: max-age=60\r\n\r\n",
            ]
        )

        class Request(BaseHTTPRequestHandler):
            # noinspection PyMissingConstructor
            def __init__(self, request_text):
                self.rfile = BytesIO(request_text)
                self.raw_requestline = self.rfile.readline()
                self.error_code = self.error_message = None
                self.parse_request()

            def send_error(self, code, message=None):
                self.error_code = code
                self.error_message = message

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.bind(("", self.__class__.ssdp_multicast_port))

        for address in self.get_interface_addresses():
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(self.__class__.ssdp_multicast_addr)
                + socket.inet_aton(address),
            )

        self._logger.info(f"Registered {self.get_instance_name()} for SSDP")

        self._ssdp_notify(alive=True)

        try:
            while self._ssdp_monitor_active:
                try:
                    data, address = sock.recvfrom(4096)
                    request = Request(data)
                    if (
                        not request.error_code
                        and request.command == "M-SEARCH"
                        and request.path == "*"
                        and (
                            request.headers["ST"] == "upnp:rootdevice"
                            or request.headers["ST"] == "ssdp:all"
                        )
                        and request.headers["MAN"] == '"ssdp:discover"'
                    ):
                        interface_address = octoprint.util.address_for_client(
                            *address,
                            addresses=self._settings.get(["addresses"]),
                            interfaces=self._settings.get(["interfaces"]),
                        )
                        if not interface_address:
                            continue

                        message = location_message.format(
                            uuid=self.get_uuid(),
                            location="http://{host}:{port}/plugin/discovery/discovery.xml".format(
                                host=interface_address, port=self.port
                            ),
                        )
                        sock.sendto(message.encode("utf-8"), address)
                        self._logger.debug(
                            "Sent M-SEARCH reply for {path} and {st} to {address!r}".format(
                                path=request.path,
                                st=request.headers["ST"],
                                address=address,
                            )
                        )
                except socket.timeout:
                    pass
                finally:
                    self._ssdp_notify(alive=True)
        finally:
            try:
                sock.close()
            except Exception:
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
            return f'OctoPrint instance "{name}"'
        else:
            return f"OctoPrint instance on {socket.gethostname()}"

    def get_interface_addresses(self):
        addresses = self._settings.get(["addresses"])
        if addresses:
            return addresses
        else:
            return list(
                octoprint.util.interface_addresses(
                    interfaces=self._settings.get(["interfaces"]),
                    ignored=self._settings.get(["ignoredInterfaces"]),
                )
            )


__plugin_name__ = "Discovery"
__plugin_author__ = "Gina Häußge"
__plugin_url__ = "https://docs.octoprint.org/en/master/bundledplugins/discovery.html"
__plugin_description__ = (
    "Makes the OctoPrint instance discoverable via Bonjour/Avahi/Zeroconf and uPnP"
)
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin your OctoPrint instance will no longer be "
    "discoverable on the network via Bonjour and uPnP."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
