__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs

CONST_15MIN = 15 * 60
CONST_1GB = 1024 * 1024 * 1024
CONST_500MB = 500 * 1024 * 1024
CONST_200MB = 200 * 1024 * 1024
CONST_100KB = 100 * 1024


@with_attrs_docs
class ReverseProxyConfig(BaseModel):
    prefixHeader: Optional[str] = None
    """The request header from which to determine the URL prefix under which OctoPrint is served by the reverse proxy."""

    schemeHeader: Optional[str] = None
    """The request header from which to determine the scheme (http or https) under which a specific request to OctoPrint was made to the reverse proxy."""

    hostHeader: Optional[str] = None
    """The request header from which to determine the host under which OctoPrint is served by the reverse proxy."""

    serverHeader: Optional[str] = None

    portHeader: Optional[str] = None

    prefixFallback: Optional[str] = None
    """Use this option to define an optional URL prefix (with a leading /, so absolute to your server's root) under which to run OctoPrint. This should only be needed if you want to run OctoPrint behind a reverse proxy under a different root endpoint than `/` and can't configure said reverse proxy to send a prefix HTTP header (X-Script-Name by default, see above) with forwarded requests."""

    schemeFallback: Optional[str] = None
    """Use this option to define an optional forced scheme (http or https) under which to run OctoPrint. This should only be needed if you want to run OctoPrint behind a reverse proxy that also does HTTPS determination but can't configure said reverse proxy to send a scheme HTTP header (X-Scheme by default, see above) with forwarded requests."""

    hostFallback: Optional[str] = None
    """Use this option to define an optional forced host under which to run OctoPrint. This should only be needed if you want to run OctoPrint behind a reverse proxy with a different hostname than OctoPrint itself but can't configure said reverse proxy to send a host HTTP header (X-Forwarded-Host by default, see above) with forwarded requests."""

    serverFallback: Optional[str] = None

    portFallback: Optional[str] = None

    trustedDownstream: List[str] = []
    """List of trusted downstream servers for which to ignore the IP address when trying to determine the connecting client's IP address. If you have OctoPrint behind more than one reverse proxy you should add their IPs here so that they won't be interpreted as the client's IP. One reverse proxy will be handled correctly by default."""


@with_attrs_docs
class UploadsConfig(BaseModel):
    maxSize: int = CONST_1GB
    """Maximum size of uploaded files in bytes, defaults to 1GB."""

    nameSuffix: str = "name"
    """Suffix used for storing the filename in the file upload headers when streaming uploads."""

    pathSuffix: str = "path"
    """Suffix used for storing the path to the temporary file in the file upload headers when streaming uploads."""


@with_attrs_docs
class CommandsConfig(BaseModel):
    systemShutdownCommand: Optional[str] = None
    """Command to shut down the system OctoPrint is running on."""

    systemRestartCommand: Optional[str] = None
    """Command to restart the system OctoPrint is running on."""

    serverRestartCommand: Optional[str] = None
    """Command to restart OctoPrint."""

    localPipCommand: Optional[str] = None
    """pip command associated with OctoPrint, used for installing plugins and updates, if unset (default) the command will be autodetected based on the current python executable - unless you have a really special setup this is the right way to do it and there should be no need to ever touch this setting."""


@with_attrs_docs
class OnlineCheckConfig(BaseModel):
    enabled: Optional[bool] = None
    """Whether the online check is enabled. Ships unset, the user will be asked to make a decision as part of the setup wizard."""

    interval: int = CONST_15MIN
    """Interval in which to check for online connectivity (in seconds), defaults to 15 minutes."""

    host: str = "1.1.1.1"
    """DNS host against which to check, defaults to Cloudflare's DNS."""

    port: int = 53
    """DNS port against which to check, defaults to the standard DNS port."""

    name: str = "octoprint.org"
    """Host name for which to check name resolution, defaults to OctoPrint's main domain."""


@with_attrs_docs
class PluginBlacklistConfig(BaseModel):
    enabled: Optional[bool] = None
    """Whether use of the blacklist is enabled. If unset, the user will be asked to make a decision as part of the setup wizard."""

    url: str = "https://plugins.octoprint.org/blacklist.json"
    """The URL from which to fetch the blacklist."""

    ttl: int = CONST_15MIN
    """Time to live of the cached blacklist, in seconds (default: 15 minutes)."""


@with_attrs_docs
class DiskspaceConfig(BaseModel):
    warning: int = CONST_500MB
    """Threshold (bytes) after which to consider disk space becoming sparse, defaults to 500MB."""

    critical: int = CONST_200MB
    """Threshold (bytes) after which to consider disk space becoming critical, defaults to 200MB."""


@with_attrs_docs
class PreemptiveCacheConfig(BaseModel):
    exceptions: List[str] = []
    """Which server paths to exclude from the preemptive cache, e.g. `/some/path`."""

    until: int = 7
    """How many days to leave unused entries in the preemptive cache config."""


@with_attrs_docs
class IpCheckConfig(BaseModel):
    enabled: bool = True
    """Whether to enable the check."""

    trustedSubnets: List[str] = []
    """Additional non-local subnets to consider trusted, in CIDR notation, e.g. `192.168.1.0/24`."""


class SameSiteEnum(str, Enum):
    strict = "Strict"
    lax = "Lax"
    none = "None"


@with_attrs_docs
class CookiesConfig(BaseModel):
    secure: bool = False
    """Whether to set the `Secure` flag to true on cookies. Only set to true if you are running OctoPrint behind a reverse proxy taking care of SSL termination."""

    samesite: Optional[SameSiteEnum] = SameSiteEnum.lax
    """`SameSite` setting to use on the cookies. Possible values are `None`, `Lax` and `Strict`. Defaults to `Lax`. Be advised that if forced unset, this has security implications as many browsers now default to `Lax` unless you configure cookies to be set with `Secure` flag set, explicitly set `SameSite` setting here and also serve OctoPrint over https. The `Lax` setting is known to cause with embedding OctoPrint in frames. See also ["Feature: Cookies default to SameSite=Lax"](https://www.chromestatus.com/feature/5088147346030592), ["Feature: Reject insecure SameSite=None cookies"](https://www.chromestatus.com/feature/5633521622188032) and [issue #3482](https://github.com/OctoPrint/OctoPrint/issues/3482)."""


@with_attrs_docs
class ServerConfig(BaseModel):
    host: Optional[str] = None
    """Use this option to define the host to which to bind the server. If unset, OctoPrint will attempt to bind on all available interfaces, IPv4 and v6 unless either is disabled."""

    port: int = 5000
    """Use this option to define the port to which to bind the server."""

    firstRun: bool = True
    """If this option is true, OctoPrint will show the First Run wizard and set the setting to false after that completes."""

    startOnceInSafeMode: bool = False
    """If this option is true, OctoPrint will enable safe mode on the next server start and reset the setting to false"""

    ignoreIncompleteStartup: bool = False
    """Set this to true to make OctoPrint ignore incomplete startups. Helpful for development."""

    incompleteStartup: bool = False
    """Signals to OctoPrint that the last startup was incomplete. OctoPrint will then startup in safe mode."""

    seenWizards: Dict[str, str] = {}

    secretKey: Optional[str] = None
    """Secret key for encrypting cookies and such, randomly generated on first run."""

    heartbeat: int = CONST_15MIN

    reverseProxy: ReverseProxyConfig = ReverseProxyConfig()
    """Settings if OctoPrint is running behind a reverse proxy (haproxy, nginx, apache, ...) that doesn't correctly set the [required headers](https://community.octoprint.org/t/reverse-proxy-configuration-examples/1107). These are necessary in order to make OctoPrint generate correct external URLs so that AJAX requests and download URLs work, and so that client IPs are read correctly."""

    uploads: UploadsConfig = UploadsConfig()
    """Settings for file uploads to OctoPrint, such as maximum allowed file size and header suffixes to use for streaming uploads. OctoPrint does some nifty things internally in order to allow streaming of large file uploads to the application rather than just storing them in memory. For that it needs to do some rewriting of the incoming upload HTTP requests, storing the uploaded file to a temporary location on disk and then sending an internal request to the application containing the original filename and the location of the temporary file."""

    maxSize: int = CONST_100KB
    """Maximum size of requests other than file uploads in bytes, defaults to 100KB."""

    commands: CommandsConfig = CommandsConfig()
    """Commands to restart/shutdown octoprint or the system it's running on."""

    onlineCheck: OnlineCheckConfig = OnlineCheckConfig()
    """Configuration of the regular online connectivity check."""

    pluginBlacklist: PluginBlacklistConfig = PluginBlacklistConfig()
    """Configuration of the plugin blacklist."""

    diskspace: DiskspaceConfig = DiskspaceConfig()
    """Settings of when to display what disk space warning."""

    preemptiveCache: PreemptiveCacheConfig = PreemptiveCacheConfig()
    """Configuration of the preemptive cache."""

    ipCheck: IpCheckConfig = IpCheckConfig()
    """Configuration of the client IP check to warn about connections from external networks."""

    allowFraming: bool = False
    """Whether to allow OctoPrint to be embedded in a frame or not. Note that depending on your setup you might have to set SameSite to None, Secure to true and serve OctoPrint through a reverse proxy that enables https for cookies and thus logging in to work."""

    cookies: CookiesConfig = CookiesConfig()
    """Settings for further configuration of the cookies that OctoPrint sets (login, remember me, ...)."""
