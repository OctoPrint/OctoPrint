# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from flask import make_response

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import functools
import io
import logging
import os
import threading
import time

import flask
import flask.json
import flask.sessions
import flask_assets
import flask_login
import netaddr
import tornado.web
import webassets.updater
import webassets.utils
from cachelib import BaseCache
from past.builtins import basestring, long
from werkzeug.local import LocalProxy
from werkzeug.utils import cached_property

import octoprint.access.users
import octoprint.plugin
import octoprint.server
import octoprint.vendor.flask_principal as flask_principal
from octoprint.events import Events, eventManager
from octoprint.settings import settings
from octoprint.util import DefaultOrderedDict, deprecated
from octoprint.util.json import JsonEncoding
from octoprint.util.net import is_lan_address

try:
    from os import scandir, walk
except ImportError:
    from scandir import scandir, walk  # noqa: F401

# ~~ monkey patching


def enable_additional_translations(default_locale="en", additional_folders=None):
    import os

    import flask_babel
    from babel import Locale, support
    from flask import _request_ctx_stack

    if additional_folders is None:
        additional_folders = []

    logger = logging.getLogger(__name__)

    def fixed_list_translations(self):
        """Returns a list of all the locales translations exist for.  The
        list returned will be filled with actual locale objects and not just
        strings.
        """

        def list_translations(dirname):
            if not os.path.isdir(dirname):
                return []
            result = []
            for entry in scandir(dirname):
                locale_dir = os.path.join(entry.path, "LC_MESSAGES")
                if not os.path.isdir(locale_dir):
                    continue
                if any(filter(lambda x: x.name.endswith(".mo"), scandir(locale_dir))):
                    result.append(Locale.parse(entry.name))
            return result

        dirs = additional_folders + [os.path.join(self.app.root_path, "translations")]

        # translations from plugins
        plugins = octoprint.plugin.plugin_manager().enabled_plugins
        for plugin in plugins.values():
            plugin_translation_dir = os.path.join(plugin.location, "translations")
            if not os.path.isdir(plugin_translation_dir):
                continue
            dirs.append(plugin_translation_dir)

        result = [Locale.parse(default_locale)]

        for dir in dirs:
            result += list_translations(dir)
        return result

    def fixed_get_translations():
        """Returns the correct gettext translations that should be used for
        this request.  This will never fail and return a dummy translation
        object if used outside of the request or if a translation cannot be
        found.
        """
        ctx = _request_ctx_stack.top
        if ctx is None:
            return None
        translations = getattr(ctx, "babel_translations", None)
        if translations is None:
            locale = flask_babel.get_locale()
            translations = support.Translations()

            if str(locale) != default_locale:
                # plugin translations
                plugins = octoprint.plugin.plugin_manager().enabled_plugins
                for name, plugin in plugins.items():
                    dirs = (
                        list(
                            map(
                                lambda x: os.path.join(x, "_plugins", name),
                                additional_folders,
                            )
                        )
                        + [os.path.join(plugin.location, "translations")]
                    )
                    for dirname in dirs:
                        if not os.path.isdir(dirname):
                            continue

                        try:
                            plugin_translations = support.Translations.load(
                                dirname, [locale]
                            )
                        except Exception:
                            logger.exception(
                                "Error while trying to load translations "
                                "for plugin {name}".format(**locals())
                            )
                        else:
                            if isinstance(plugin_translations, support.Translations):
                                translations = translations.merge(plugin_translations)
                                logger.debug(
                                    "Using translation plugin folder {dirname} from "
                                    "plugin {name} for locale {locale}".format(**locals())
                                )
                                break
                    else:
                        logger.debug(
                            "No translations for locale {locale} "
                            "from plugin {name}".format(**locals())
                        )

                # core translations
                dirs = additional_folders + [
                    os.path.join(ctx.app.root_path, "translations")
                ]
                for dirname in dirs:
                    core_translations = support.Translations.load(dirname, [locale])
                    if isinstance(core_translations, support.Translations):
                        logger.debug(
                            "Using translation core folder {dirname} "
                            "for locale {locale}".format(**locals())
                        )
                        break
                else:
                    logger.debug(
                        "No translations for locale {} in core folders".format(locale)
                    )
                translations = translations.merge(core_translations)

            ctx.babel_translations = translations
        return translations

    flask_babel.Babel.list_translations = fixed_list_translations
    flask_babel.get_translations = fixed_get_translations


def fix_webassets_cache():
    from webassets import cache

    error_logger = logging.getLogger(__name__ + ".fix_webassets_cache")

    def fixed_set(self, key, data):
        import os
        import pickle
        import shutil
        import tempfile

        if not os.path.exists(self.directory):
            error_logger.warning(
                "Cache directory {} doesn't exist, not going "
                "to attempt to write cache file".format(self.directory)
            )

        md5 = "%s" % cache.make_md5(self.V, key)
        filename = os.path.join(self.directory, md5)
        fd, temp_filename = tempfile.mkstemp(prefix="." + md5, dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as f:
                pickle.dump(data, f)
                f.flush()
            shutil.move(temp_filename, filename)
        except Exception:
            os.remove(temp_filename)
            raise

    def fixed_get(self, key):
        import errno
        import os
        import warnings

        from webassets.cache import make_md5

        if not os.path.exists(self.directory):
            error_logger.warning(
                "Cache directory {} doesn't exist, not going "
                "to attempt to read cache file".format(self.directory)
            )
            return None

        try:
            hash = make_md5(self.V, key)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            return None

        filename = os.path.join(self.directory, "%s" % hash)
        try:
            f = io.open(filename, "rb")
        except IOError as e:
            if e.errno != errno.ENOENT:
                error_logger.exception(
                    "Got an exception while trying to open webasset file {}".format(
                        filename
                    )
                )
            return None
        try:
            result = f.read()
        finally:
            f.close()

        unpickled = webassets.cache.safe_unpickle(result)
        if unpickled is None:
            warnings.warn("Ignoring corrupted cache file %s" % filename)
        return unpickled

    cache.FilesystemCache.set = fixed_set
    cache.FilesystemCache.get = fixed_get


def fix_webassets_filtertool():
    from webassets.merge import FilterTool, MemoryHunk, log

    error_logger = logging.getLogger(__name__ + ".fix_webassets_filtertool")

    def fixed_wrap_cache(self, key, func):
        """Return cache value ``key``, or run ``func``."""
        if self.cache:
            if not self.no_cache_read:
                log.debug("Checking cache for key %s", key)
                content = self.cache.get(key)
                if content not in (False, None):
                    log.debug("Using cached result for %s", key)
                    return MemoryHunk(content)

        try:
            content = func().getvalue()
            if self.cache:
                try:
                    log.debug(
                        "Storing result in cache with key %s",
                        key,
                    )
                    self.cache.set(key, content)
                except Exception:
                    error_logger.exception(
                        "Got an exception while trying to save file to cache, not caching"
                    )
            return MemoryHunk(content)
        except Exception:
            error_logger.exception(
                "Got an exception while trying to apply filter, ignoring file"
            )
            return MemoryHunk("")

    FilterTool._wrap_cache = fixed_wrap_cache


def fix_flask_jsonify():
    def fixed_jsonify(*args, **kwargs):
        """Backported from https://github.com/pallets/flask/blob/7e714bd28b6e96d82b2848b48cf8ff48b517b09b/flask/json/__init__.py#L257"""
        from flask.json import current_app, dumps

        indent = None
        separators = (",", ":")

        if current_app.config["JSONIFY_PRETTYPRINT_REGULAR"] or current_app.debug:
            indent = 2
            separators = (", ", ": ")

        if args and kwargs:
            raise TypeError(
                "jsonify() behavior undefined when passed both args and kwargs"
            )
        elif len(args) == 1:  # single args are passed directly to dumps()
            data = args[0]
        else:
            data = args or kwargs

        return current_app.response_class(
            dumps(data, indent=indent, separators=separators, allow_nan=False) + "\n",
            mimetype="application/json",
        )

    flask.jsonify = fixed_jsonify


# ~~ WSGI environment wrapper for reverse proxying


class ReverseProxiedEnvironment(object):
    @staticmethod
    def to_header_candidates(values):
        if values is None:
            return []
        if not isinstance(values, (list, tuple)):
            values = [values]
        to_wsgi_format = lambda header: "HTTP_" + header.upper().replace("-", "_")
        return list(map(to_wsgi_format, values))

    @staticmethod
    def valid_ip(address):
        import netaddr

        try:
            netaddr.IPAddress(address)
            return True
        except Exception:
            return False

    def __init__(
        self,
        header_prefix=None,
        header_scheme=None,
        header_host=None,
        header_server=None,
        header_port=None,
        prefix=None,
        scheme=None,
        host=None,
        server=None,
        port=None,
    ):

        # sensible defaults
        if header_prefix is None:
            header_prefix = ["x-script-name"]
        if header_scheme is None:
            header_scheme = ["x-forwarded-proto", "x-scheme"]
        if header_host is None:
            header_host = ["x-forwarded-host"]
        if header_server is None:
            header_server = ["x-forwarded-server"]
        if header_port is None:
            header_port = ["x-forwarded-port"]

        # header candidates
        self._headers_prefix = self.to_header_candidates(header_prefix)
        self._headers_scheme = self.to_header_candidates(header_scheme)
        self._headers_host = self.to_header_candidates(header_host)
        self._headers_server = self.to_header_candidates(header_server)
        self._headers_port = self.to_header_candidates(header_port)

        # fallback prefix & scheme & host from config
        self._fallback_prefix = prefix
        self._fallback_scheme = scheme
        self._fallback_host = host
        self._fallback_server = server
        self._fallback_port = port

    def __call__(self, environ):
        def retrieve_header(header_type):
            candidates = getattr(self, "_headers_" + header_type, [])
            fallback = getattr(self, "_fallback_" + header_type, None)

            for candidate in candidates:
                value = environ.get(candidate, None)
                if value is not None:
                    return value
            else:
                return fallback

        def host_to_server_and_port(host, scheme):
            if host is None:
                return None, None

            default_port = "443" if scheme == "https" else "80"
            host = host.strip()

            if ":" in host:
                # we might have an ipv6 address here, or a port, or both

                if host[0] == "[":
                    # that looks like an ipv6 address with port, e.g. [fec1::1]:80
                    address_end = host.find("]")
                    if address_end == -1:
                        # no ], that looks like a seriously broken address
                        return None, None

                    # extract server ip, skip enclosing [ and ]
                    server = host[1:address_end]
                    tail = host[address_end + 1 :]

                    # now check if there's also a port
                    if len(tail) and tail[0] == ":":
                        # port included as well
                        port = tail[1:]
                    else:
                        # no port, use default one
                        port = default_port

                elif self.__class__.valid_ip(host):
                    # ipv6 address without port
                    server = host
                    port = default_port

                else:
                    # ipv4 address with port
                    server, port = host.rsplit(":", 1)

            else:
                server = host
                port = default_port

            return server, port

        # determine prefix
        prefix = retrieve_header("prefix")
        if prefix is not None:
            environ["SCRIPT_NAME"] = prefix
            path_info = environ["PATH_INFO"]
            if path_info.startswith(prefix):
                environ["PATH_INFO"] = path_info[len(prefix) :]

        # determine scheme
        scheme = retrieve_header("scheme")
        if scheme is not None and "," in scheme:
            # Scheme might be something like "https,https" if doubly-reverse-proxied
            # without stripping original scheme header first, make sure to only use
            # the first entry in such a case. See #1391.
            scheme, _ = map(lambda x: x.strip(), scheme.split(",", 1))
        if scheme is not None:
            environ["wsgi.url_scheme"] = scheme

        # determine host
        url_scheme = environ["wsgi.url_scheme"]
        host = retrieve_header("host")
        if host is not None:
            # if we have a host, we take server_name and server_port from it
            server, port = host_to_server_and_port(host, url_scheme)
            environ["HTTP_HOST"] = host
            environ["SERVER_NAME"] = server
            environ["SERVER_PORT"] = port

        elif environ.get("HTTP_HOST", None) is not None:
            # if we have a Host header, we use that and make sure our server name and port properties match it
            host = environ["HTTP_HOST"]
            server, port = host_to_server_and_port(host, url_scheme)
            environ["SERVER_NAME"] = server
            environ["SERVER_PORT"] = port

        else:
            # else we take a look at the server and port headers and if we have
            # something there we derive the host from it

            # determine server - should usually not be used
            server = retrieve_header("server")
            if server is not None:
                environ["SERVER_NAME"] = server

            # determine port - should usually not be used
            port = retrieve_header("port")
            if port is not None:
                environ["SERVER_PORT"] = port

            # reconstruct host header
            if (
                url_scheme == "http"
                and environ["SERVER_PORT"] == "80"
                or url_scheme == "https"
                and environ["SERVER_PORT"] == "443"
            ):
                # default port for scheme, can be skipped
                environ["HTTP_HOST"] = environ["SERVER_NAME"]
            else:
                server_name_component = environ["SERVER_NAME"]
                if ":" in server_name_component and self.__class__.valid_ip(
                    server_name_component
                ):
                    # this is an ipv6 address, we need to wrap that in [ and ] before appending the port
                    server_name_component = "[" + server_name_component + "]"

                environ["HTTP_HOST"] = (
                    server_name_component + ":" + environ["SERVER_PORT"]
                )

        # call wrapped app with rewritten environment
        return environ


# ~~ request and response versions


class OctoPrintFlaskRequest(flask.Request):
    environment_wrapper = staticmethod(lambda x: x)

    def __init__(self, environ, *args, **kwargs):
        # apply environment wrapper to provided WSGI environment
        flask.Request.__init__(self, self.environment_wrapper(environ), *args, **kwargs)

    @cached_property
    def cookies(self):
        # strip cookie_suffix from all cookies in the request, return result
        cookies = flask.Request.cookies.__get__(self)

        result = {}
        desuffixed = {}
        for key, value in cookies.items():
            if key.endswith(self.cookie_suffix):
                desuffixed[key[: -len(self.cookie_suffix)]] = value
            else:
                result[key] = value

        result.update(desuffixed)
        return result

    @cached_property
    def server_name(self):
        """Short cut to the request's server name header"""
        return self.environ.get("SERVER_NAME")

    @cached_property
    def server_port(self):
        """Short cut to the request's server port header"""
        return self.environ.get("SERVER_PORT")

    @cached_property
    def cookie_suffix(self):
        """
        Request specific suffix for set and read cookies

        We need this because cookies are not port-specific and we don't want to overwrite our
        session and other cookies from one OctoPrint instance on our machine with those of another
        one who happens to listen on the same address albeit a different port or script root.
        """
        result = "_P" + self.server_port
        if self.script_root:
            return result + "_R" + self.script_root.replace("/", "|")
        return result


class OctoPrintFlaskResponse(flask.Response):
    def set_cookie(self, key, *args, **kwargs):
        # restrict cookie path to script root
        kwargs["path"] = flask.request.script_root + kwargs.get("path", "/")

        # set same-site header
        samesite = settings().get(["server", "cookies", "samesite"])
        if samesite is not None:
            samesite = samesite.lower()
        if samesite == "none":
            samesite = None
        if samesite not in (None, "strict", "lax"):
            samesite = None
        kwargs["samesite"] = samesite

        # set secure if necessary
        kwargs["secure"] = settings().getBoolean(["server", "cookies", "secure"])

        # add request specific cookie suffix to name
        flask.Response.set_cookie(
            self, key + flask.request.cookie_suffix, *args, **kwargs
        )

    def delete_cookie(self, key, path="/", domain=None):
        flask.Response.delete_cookie(self, key, path=path, domain=domain)

        # we also still might have a cookie left over from before we started prefixing, delete that manually
        # without any pre processing (no path prefix, no key suffix)
        flask.Response.set_cookie(
            self, key, expires=0, max_age=0, path=path, domain=domain
        )


class OctoPrintSessionInterface(flask.sessions.SecureCookieSessionInterface):
    def should_set_cookie(self, app, session):
        return flask.request.endpoint != "static"

    def save_session(self, app, session, response):
        if flask.g.get("login_via_apikey", False):
            return
        return super(OctoPrintSessionInterface, self).save_session(app, session, response)


# ~~ passive login helper

_cached_local_networks = None


def _local_networks():
    global _cached_local_networks

    if _cached_local_networks is None:
        logger = logging.getLogger(__name__)
        local_networks = netaddr.IPSet([])
        for entry in settings().get(["accessControl", "localNetworks"]):
            network = netaddr.IPNetwork(entry)
            local_networks.add(network)
            logger.debug("Added network {} to localNetworks".format(network))

            if network.version == 4:
                network_v6 = network.ipv6()
                local_networks.add(network_v6)
                logger.debug(
                    "Also added v6 representation of v4 network {} = {} to localNetworks".format(
                        network, network_v6
                    )
                )

        _cached_local_networks = local_networks

    return _cached_local_networks


def passive_login():
    logger = logging.getLogger(__name__)

    user = flask_login.current_user

    remote_address = get_remote_address(flask.request)
    ip_check_enabled = settings().getBoolean(["server", "ipCheck", "enabled"])
    ip_check_trusted = settings().get(["server", "ipCheck", "trustedSubnets"])

    if isinstance(user, LocalProxy):
        # noinspection PyProtectedMember
        user = user._get_current_object()

    def login(u):
        # login known user
        if not u.is_anonymous:
            u = octoprint.server.userManager.login_user(u)
        flask_login.login_user(u)
        flask_principal.identity_changed.send(
            flask.current_app._get_current_object(),
            identity=flask_principal.Identity(u.get_id()),
        )
        if hasattr(u, "session"):
            flask.session["usersession.id"] = u.session
        flask.g.user = u

        eventManager().fire(Events.USER_LOGGED_IN, payload={"username": u.get_id()})

        return u

    def determine_user(u):
        if not u.is_anonymous and u.is_active:
            # known active user
            logger.info(
                "Passively logging in user {} from {}".format(u.get_id(), remote_address)
            )

        elif (
            settings().getBoolean(["accessControl", "autologinLocal"])
            and settings().get(["accessControl", "autologinAs"]) is not None
            and settings().get(["accessControl", "localNetworks"]) is not None
            and "active_logout" not in flask.request.cookies
            and remote_address
        ):
            # attempt local autologin
            autologin_as = settings().get(["accessControl", "autologinAs"])
            local_networks = _local_networks()
            logger.debug(
                "Checking if remote address {} is in localNetworks ({!r})".format(
                    remote_address, local_networks
                )
            )

            try:
                if netaddr.IPAddress(remote_address) in local_networks:
                    autologin_user = octoprint.server.userManager.find_user(autologin_as)
                    if autologin_user is not None and autologin_user.is_active:
                        logger.info(
                            "Passively logging in user {} from {} via autologin".format(
                                autologin_as, remote_address
                            )
                        )
                        flask.session["login_mechanism"] = "autologin"
                        return autologin_user
            except Exception:
                logger.exception(
                    "Could not autologin user {} from {} for networks {}".format(
                        autologin_as, remote_address, local_networks
                    )
                )

        if not u.is_active:
            # inactive user, switch to anonymous
            u = octoprint.server.userManager.anonymous_user_factory()

        return u

    user = login(determine_user(user))
    response = user.as_dict()
    response["_is_external_client"] = ip_check_enabled and not is_lan_address(
        remote_address, additional_private=ip_check_trusted
    )
    if flask.session.get("login_mechanism") is not None:
        response["_login_mechanism"] = flask.session.get("login_mechanism")
    return flask.jsonify(response)


# ~~ cache decorator for cacheable views


class LessSimpleCache(BaseCache):
    """
    Slightly improved version of :class:`SimpleCache`.

    Setting ``default_timeout`` or ``timeout`` to ``-1`` will have no timeout be applied at all.
    """

    def __init__(self, threshold=500, default_timeout=300):
        BaseCache.__init__(self, default_timeout=default_timeout)
        self._mutex = threading.RLock()
        self._cache = {}
        self._bypassed = set()
        self.clear = self._cache.clear
        self._threshold = threshold

    def _prune(self):
        if self.over_threshold():
            now = time.time()
            for idx, (key, (expires, _)) in enumerate(self._cache.items()):
                if expires is not None and expires <= now or idx % 3 == 0:
                    with self._mutex:
                        self._cache.pop(key, None)

    def get(self, key):
        import pickle

        now = time.time()
        with self._mutex:
            expires, value = self._cache.get(key, (0, None))
        if expires is None or expires > now:
            return pickle.loads(value)

    def set(self, key, value, timeout=None):
        import pickle

        with self._mutex:
            self._prune()
            self._cache[key] = (
                self.calculate_timeout(timeout=timeout),
                pickle.dumps(value, pickle.HIGHEST_PROTOCOL),
            )
            if key in self._bypassed:
                self._bypassed.remove(key)

    def add(self, key, value, timeout=None):
        with self._mutex:
            self.set(key, value, timeout=None)
            self._cache.setdefault(key, self._cache[key])

    def delete(self, key):
        with self._mutex:
            self._cache.pop(key, None)

    def calculate_timeout(self, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        if timeout == -1:
            return None
        return time.time() + timeout

    def over_threshold(self):
        if self._threshold is None:
            return False
        with self._mutex:
            return len(self._cache) > self._threshold

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __delitem__(self, key):
        return self.delete(key)

    def __contains__(self, key):
        with self._mutex:
            return key in self._cache

    def set_bypassed(self, key):
        with self._mutex:
            self._bypassed.add(key)

    def is_bypassed(self, key):
        with self._mutex:
            return key in self._bypassed


_cache = LessSimpleCache()


def cached(
    timeout=5 * 60,
    key=lambda: "view:%s" % flask.request.path,
    unless=None,
    refreshif=None,
    unless_response=None,
):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            logger = logging.getLogger(__name__)

            cache_key = key()

            def f_with_duration(*args, **kwargs):
                start_time = time.time()
                try:
                    return f(*args, **kwargs)
                finally:
                    elapsed = time.time() - start_time
                    logger.debug(
                        "Needed {elapsed:.2f}s to render {path} (key: {key})".format(
                            elapsed=elapsed, path=flask.request.path, key=cache_key
                        )
                    )

            # bypass the cache if "unless" condition is true
            if callable(unless) and unless():
                logger.debug(
                    "Cache for {path} bypassed, calling wrapped function".format(
                        path=flask.request.path
                    )
                )
                _cache.set_bypassed(cache_key)
                return f_with_duration(*args, **kwargs)

            # also bypass the cache if it's disabled completely
            if not settings().getBoolean(["devel", "cache", "enabled"]):
                logger.debug(
                    "Cache for {path} disabled, calling wrapped function".format(
                        path=flask.request.path
                    )
                )
                _cache.set_bypassed(cache_key)
                return f_with_duration(*args, **kwargs)

            rv = _cache.get(cache_key)

            # only take the value from the cache if we are not required to refresh it from the wrapped function
            if rv is not None and (not callable(refreshif) or not refreshif(rv)):
                logger.debug(
                    "Serving entry for {path} from cache (key: {key})".format(
                        path=flask.request.path, key=cache_key
                    )
                )
                if "X-From-Cache" not in rv.headers:
                    rv.headers["X-From-Cache"] = "true"
                return rv

            # get value from wrapped function
            logger.debug(
                "No cache entry or refreshing cache for {path} (key: {key}), calling wrapped function".format(
                    path=flask.request.path, key=cache_key
                )
            )
            rv = f_with_duration(*args, **kwargs)

            # do not store if the "unless_response" condition is true
            if callable(unless_response) and unless_response(rv):
                logger.debug(
                    "Not caching result for {path} (key: {key}), bypassed".format(
                        path=flask.request.path, key=cache_key
                    )
                )
                _cache.set_bypassed(cache_key)
                return rv

            # store it in the cache
            _cache.set(cache_key, rv, timeout=timeout)

            return rv

        return decorated_function

    return decorator


def is_in_cache(key=lambda: "view:%s" % flask.request.path):
    if callable(key):
        key = key()
    return key in _cache


def is_cache_bypassed(key=lambda: "view:%s" % flask.request.path):
    if callable(key):
        key = key()
    return _cache.is_bypassed(key)


def cache_check_headers():
    return "no-cache" in flask.request.cache_control or "no-cache" in flask.request.pragma


def cache_check_response_headers(response):
    if not isinstance(response, flask.Response):
        return False

    headers = response.headers

    if "Cache-Control" in headers and (
        "no-cache" in headers["Cache-Control"] or "no-store" in headers["Cache-Control"]
    ):
        return True

    if "Pragma" in headers and "no-cache" in headers["Pragma"]:
        return True

    if "Expires" in headers and headers["Expires"] in ("0", "-1"):
        return True

    return False


def cache_check_status_code(response, valid):
    if not isinstance(response, flask.Response):
        return False

    if callable(valid):
        return not valid(response.status_code)
    else:
        return response.status_code not in valid


class PreemptiveCache(object):
    def __init__(self, cachefile):
        self.cachefile = cachefile
        self.environment = None

        self._logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

        self._lock = threading.RLock()

    def record(self, data, unless=None, root=None):
        if callable(unless) and unless():
            return

        entry_data = data
        if callable(entry_data):
            entry_data = entry_data()

        if entry_data is not None:
            if root is None:
                from flask import request

                root = request.path
            self.add_data(root, entry_data)

    def has_record(self, data, root=None):
        if callable(data):
            data = data()

        if data is None:
            return False

        if root is None:
            from flask import request

            root = request.path

        all_data = self.get_data(root)
        for existing in all_data:
            if self._compare_data(data, existing):
                return True

        return False

    def clean_all_data(self, cleanup_function):
        assert callable(cleanup_function)

        with self._lock:
            all_data = self.get_all_data()
            for root, entries in list(all_data.items()):
                old_count = len(entries)
                entries = cleanup_function(root, entries)
                if not entries:
                    del all_data[root]
                    self._logger.debug(
                        "Removed root {} from preemptive cache".format(root)
                    )
                elif len(entries) < old_count:
                    all_data[root] = entries
                    self._logger.debug(
                        "Removed {} entries from preemptive cache for root {}".format(
                            old_count - len(entries), root
                        )
                    )
            self.set_all_data(all_data)

        return all_data

    def get_all_data(self):
        import yaml

        cache_data = None
        with self._lock:
            try:
                with io.open(self.cachefile, "rt") as f:
                    cache_data = yaml.safe_load(f)
            except IOError as e:
                import errno

                if e.errno != errno.ENOENT:
                    raise
            except Exception:
                self._logger.exception("Error while reading {}".format(self.cachefile))

        if cache_data is None:
            cache_data = {}

        if not self._validate_data(cache_data):
            self._logger.warning("Preemptive cache data was invalid, ignoring it")
            cache_data = {}

        return cache_data

    def get_data(self, root):
        cache_data = self.get_all_data()
        return cache_data.get(root, list())

    def set_all_data(self, data):
        import yaml

        from octoprint.util import atomic_write

        with self._lock:
            try:
                with atomic_write(self.cachefile, "wt", max_permissions=0o666) as handle:
                    yaml.safe_dump(
                        data,
                        handle,
                        default_flow_style=False,
                        indent=4,
                        allow_unicode=True,
                    )
            except Exception:
                self._logger.exception("Error while writing {}".format(self.cachefile))

    def set_data(self, root, data):
        with self._lock:
            all_data = self.get_all_data()
            all_data[root] = data
            self.set_all_data(all_data)

    def add_data(self, root, data):
        def split_matched_and_unmatched(entry, entries):
            matched = []
            unmatched = []

            for e in entries:
                if self._compare_data(e, entry):
                    matched.append(e)
                else:
                    unmatched.append(e)

            return matched, unmatched

        with self._lock:
            cache_data = self.get_all_data()

            if root not in cache_data:
                cache_data[root] = []

            existing, other = split_matched_and_unmatched(data, cache_data[root])

            def get_newest(entries):
                result = None
                for entry in entries:
                    if "_timestamp" in entry and (
                        result is None
                        or (
                            "_timestamp" in result
                            and result["_timestamp"] < entry["_timestamp"]
                        )
                    ):
                        result = entry
                return result

            to_persist = get_newest(existing)
            if not to_persist:
                import copy

                to_persist = copy.deepcopy(data)
                to_persist["_timestamp"] = time.time()
                to_persist["_count"] = 1
                self._logger.info("Adding entry for {} and {!r}".format(root, to_persist))
            else:
                to_persist["_timestamp"] = time.time()
                to_persist["_count"] = to_persist.get("_count", 0) + 1
                self._logger.debug(
                    "Updating timestamp and counter for {} and {!r}".format(root, data)
                )

            self.set_data(root, [to_persist] + other)

    def _compare_data(self, a, b):
        from octoprint.util import dict_filter

        def strip_ignored(d):
            return dict_filter(d, lambda k, v: not k.startswith("_"))

        return set(strip_ignored(a).items()) == set(strip_ignored(b).items())

    def _validate_data(self, data):
        if not isinstance(data, dict):
            return False

        for entries in data.values():
            if not isinstance(entries, list):
                return False

            for entry in entries:
                if not self._validate_entry(entry):
                    return False

        return True

    def _validate_entry(self, entry):
        return isinstance(entry, dict) and "_timestamp" in entry and "_count" in entry


def preemptively_cached(cache, data, unless=None):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                cache.record(data, unless=unless)
            except Exception:
                logging.getLogger(__name__).exception(
                    "Error while recording preemptive cache entry: {!r}".format(data)
                )
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def etagged(etag):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            rv = f(*args, **kwargs)
            if isinstance(rv, flask.Response):
                try:
                    result = etag
                    if callable(result):
                        result = result(rv)
                    if result:
                        rv.set_etag(result)
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Error while calculating the etag value for response {!r}".format(
                            rv
                        )
                    )
            return rv

        return decorated_function

    return decorator


def lastmodified(date):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            rv = f(*args, **kwargs)
            if "Last-Modified" not in rv.headers:
                try:
                    result = date
                    if callable(result):
                        result = result(rv)

                    if not isinstance(result, basestring):
                        from werkzeug.http import http_date

                        result = http_date(result)

                    if result:
                        rv.headers["Last-Modified"] = result
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Error while calculating the lastmodified value for response {!r}".format(
                            rv
                        )
                    )
            return rv

        return decorated_function

    return decorator


def conditional(condition, met):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if callable(condition) and condition():
                    # condition has been met, return met-response
                    rv = met
                    if callable(met):
                        rv = met()
                    return rv
            except Exception:
                logging.getLogger(__name__).exception(
                    "Error while evaluating conditional {!r} or met {!r}".format(
                        condition, met
                    )
                )

            # condition hasn't been met, call decorated function
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def with_client_revalidation(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        r = f(*args, **kwargs)

        if isinstance(r, flask.Response):
            r = add_revalidation_response_headers(r)

        return r

    return decorated_function


def with_revalidation_checking(
    etag_factory=None, lastmodified_factory=None, condition=None, unless=None
):
    if etag_factory is None:

        def etag_factory(lm=None):
            return None

    if lastmodified_factory is None:

        def lastmodified_factory():
            return None

    if condition is None:

        def condition(lm=None, etag=None):
            if lm is None:
                lm = lastmodified_factory()

            if etag is None:
                etag = etag_factory(lm=lm)

            if flask.request.if_none_match and flask.request.if_modified_since:
                # use both
                return check_lastmodified(lm) and check_etag(etag)
            elif flask.request.if_none_match:
                # use only ETag
                return check_etag(etag)
            elif flask.request.if_modified_since:
                # use only Last-Modified
                return check_lastmodified(lm)
            else:
                # assume stale cache
                return False

    if unless is None:

        def unless():
            return False

    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            lm = lastmodified_factory()
            etag = etag_factory(lm)

            if condition(lm, etag) and not unless():
                return make_response("Not Modified", 304)

            # generate response
            response = f(*args, **kwargs)

            # set etag header if not already set
            if etag and response.get_etag()[0] is None:
                response.set_etag(etag)

            # set last modified header if not already set
            if lm and response.headers.get("Last-Modified", None) is None:
                if not isinstance(lm, basestring):
                    from werkzeug.http import http_date

                    lm = http_date(lm)
                response.headers["Last-Modified"] = lm

            response = add_no_max_age_response_headers(response)
            return response

        return decorated_function

    return decorator


def check_etag(etag):
    if etag is None:
        return False

    return (
        flask.request.method in ("GET", "HEAD")
        and flask.request.if_none_match is not None
        and etag in flask.request.if_none_match
    )


def check_lastmodified(lastmodified):
    if lastmodified is None:
        return False

    from datetime import datetime

    if isinstance(lastmodified, (int, long, float)):
        # max(86400, lastmodified) is workaround for https://bugs.python.org/issue29097,
        # present in CPython 3.6.x up to 3.7.1.
        #
        # I think it's fair to say that we'll never encounter lastmodified values older than
        # 1970-01-02 so this is a safe workaround.
        lastmodified = datetime.fromtimestamp(max(86400, lastmodified)).replace(
            microsecond=0
        )

    if not isinstance(lastmodified, datetime):
        raise ValueError(
            "lastmodified must be a datetime or float or int instance but, got {} instead".format(
                lastmodified.__class__
            )
        )

    return (
        flask.request.method in ("GET", "HEAD")
        and flask.request.if_modified_since is not None
        and lastmodified <= flask.request.if_modified_since
    )


def add_revalidation_response_headers(response):
    import werkzeug.http

    cache_control = werkzeug.http.parse_dict_header(
        response.headers.get("Cache-Control", "")
    )
    if "no-cache" not in cache_control:
        cache_control["no-cache"] = None
    if "must-revalidate" not in cache_control:
        cache_control["must-revalidate"] = None
    response.headers["Cache-Control"] = werkzeug.http.dump_header(cache_control)

    return response


def add_non_caching_response_headers(response):
    import werkzeug.http

    cache_control = werkzeug.http.parse_dict_header(
        response.headers.get("Cache-Control", "")
    )
    if "no-store" not in cache_control:
        cache_control["no-store"] = None
    if "no-cache" not in cache_control:
        cache_control["no-cache"] = None
    if "must-revalidate" not in cache_control:
        cache_control["must-revalidate"] = None
    if "post-check" not in cache_control or cache_control["post-check"] != "0":
        cache_control["post-check"] = "0"
    if "pre-check" not in cache_control or cache_control["pre-check"] != "0":
        cache_control["pre-check"] = "0"
    if "max-age" not in cache_control or cache_control["max-age"] != "0":
        cache_control["max-age"] = "0"
    response.headers["Cache-Control"] = werkzeug.http.dump_header(cache_control)

    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response


def add_no_max_age_response_headers(response):
    import werkzeug.http

    cache_control = werkzeug.http.parse_dict_header(
        response.headers.get("Cache-Control", "")
    )
    if "max-age" not in cache_control or cache_control["max-age"] != "0":
        cache_control["max-age"] = "0"
    response.headers["Cache-Control"] = werkzeug.http.dump_header(cache_control)

    return response


# ~~ access validators for use with tornado


def permission_validator(request, permission):
    """
    Validates that the given request is made by an authorized user, identified either by API key or existing Flask
    session.

    Must be executed in an existing Flask request context!

    :param request: The Flask request object
    :param request: The required permission
    """

    user = get_flask_user_from_request(request)
    if not user.has_permission(permission):
        raise tornado.web.HTTPError(403)


@deprecated(
    "admin_validator is deprecated, please use new permission_validator", since=""
)
def admin_validator(request):
    from octoprint.access.permissions import Permissions

    return permission_validator(request, Permissions.ADMIN)


@deprecated("user_validator is deprecated, please use new permission_validator", since="")
def user_validator(request):
    return True


def get_flask_user_from_request(request):
    """
    Retrieves the current flask user from the request context. Uses API key if available, otherwise the current
    user session if available.

    :param request: flask request from which to retrieve the current user
    :return: the user (might be an anonymous user)
    """
    import flask_login

    import octoprint.server.util

    user = None

    apikey = octoprint.server.util.get_api_key(request)
    if apikey is not None:
        # user from api key?
        user = octoprint.server.util.get_user_for_apikey(apikey)

    if user is None:
        # user still None -> current session user
        user = flask_login.current_user

    if user is None:
        # user still None -> anonymous
        from octoprint.server import userManager

        user = userManager.anonymous_user_factory()

    return user


def redirect_to_tornado(request, target, code=302):
    """
    Redirects from flask to tornado, flask request context must exist.

    :param request:
    :param target:
    :param code:
    :return:
    """

    import flask

    requestUrl = request.url
    appBaseUrl = requestUrl[: requestUrl.find(flask.url_for("index") + "api")]

    redirectUrl = appBaseUrl + target
    if "?" in requestUrl:
        fragment = requestUrl[requestUrl.rfind("?") :]
        redirectUrl += fragment
    return flask.redirect(redirectUrl, code=code)


def restricted_access(func):
    """
    This combines :py:func:`no_firstrun_access` and ``login_required``.
    """

    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        return no_firstrun_access(flask_login.login_required(func))(*args, **kwargs)

    return decorated_view


def no_firstrun_access(func):
    """
    If you decorate a view with this, it will ensure that first setup has been
    done for OctoPrint's Access Control.

    If OctoPrint's Access Control has not been setup yet (indicated by the userManager
    not reporting that its user database has been customized from default), the decorator
    will cause a HTTP 403 status code to be returned by the decorated resource.
    """

    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        # if OctoPrint hasn't been set up yet, abort
        if settings().getBoolean(["server", "firstRun"]) and (
            octoprint.server.userManager is None
            or not octoprint.server.userManager.has_been_customized()
        ):
            return flask.make_response("OctoPrint isn't setup yet", 403)
        return func(*args, **kwargs)

    return decorated_view


def firstrun_only_access(func):
    """
    If you decorate a view with this, it will ensure that first setup has _not_ been
    done for OctoPrint's Access Control. Otherwise it
    will cause a HTTP 403 status code to be returned by the decorated resource.
    """

    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        # if OctoPrint has been set up yet, abort
        if settings().getBoolean(["server", "firstRun"]) and (
            octoprint.server.userManager is None
            or not octoprint.server.userManager.has_been_customized()
        ):
            return func(*args, **kwargs)
        else:
            return flask.make_response(
                "OctoPrint is already setup, this resource is not longer available.", 403
            )

    return decorated_view


def get_remote_address(request):
    forwardedFor = request.headers.get("X-Forwarded-For", None)
    if forwardedFor is not None:
        return forwardedFor.split(",")[0]
    return request.remote_addr


def get_json_command_from_request(request, valid_commands):
    content_type = request.headers.get("Content-Type", None)
    if content_type is None or "application/json" not in content_type:
        return None, None, make_response("Expected content-type JSON", 400)

    data = request.get_json()
    if data is None:
        return (
            None,
            None,
            make_response("Malformed JSON body or wrong content-type in request", 400),
        )
    if "command" not in data or data["command"] not in valid_commands:
        return None, None, make_response("Expected valid command", 400)

    command = data["command"]
    for parameter in valid_commands[command]:
        if parameter not in data:
            return (
                None,
                None,
                make_response(
                    "Mandatory parameter %s missing for command %s"
                    % (parameter, command),
                    400,
                ),
            )

    return command, data, None


##~~ Flask-Assets resolver with plugin asset support


class PluginAssetResolver(flask_assets.FlaskResolver):
    def split_prefix(self, ctx, item):
        app = ctx.environment._app
        if item.startswith("plugin/"):
            try:
                prefix, plugin, name = item.split("/", 2)
                blueprint = prefix + "." + plugin

                directory = flask_assets.get_static_folder(app.blueprints[blueprint])
                item = name
                endpoint = blueprint + ".static"
                return directory, item, endpoint
            except (ValueError, KeyError):
                pass

        return flask_assets.FlaskResolver.split_prefix(self, ctx, item)

    def resolve_output_to_path(self, ctx, target, bundle):
        import os

        return os.path.normpath(os.path.join(ctx.environment.directory, target))


##~~ Webassets updater that takes changes in the configuration into account


class SettingsCheckUpdater(webassets.updater.BaseUpdater):

    updater = "always"

    def __init__(self):
        self._delegate = webassets.updater.get_updater(self.__class__.updater)

    def needs_rebuild(self, bundle, ctx):
        return self._delegate.needs_rebuild(bundle, ctx) or self.changed_settings(ctx)

    def changed_settings(self, ctx):
        if not ctx.cache:
            return False

        cache_key = ("octo", "settings")
        current_hash = settings().effective_hash
        cached_hash = ctx.cache.get(cache_key)
        # This may seem counter-intuitive, but if no cache entry is found
        # then we actually return "no update needed". This is because
        # otherwise if no cache / a dummy cache is used, then we would be
        # rebuilding every single time.
        if cached_hash is not None:
            return cached_hash != current_hash
        return False

    def build_done(self, bundle, ctx):
        self._delegate.build_done(bundle, ctx)
        if not ctx.cache:
            return

        cache_key = ("octo", "settings")
        ctx.cache.set(cache_key, settings().effective_hash)


##~~ core assets collector
def collect_core_assets(preferred_stylesheet="css"):
    assets = {"js": [], "clientjs": [], "css": [], "less": []}
    assets["js"] = [
        "js/app/bindings/allowbindings.js",
        "js/app/bindings/contextmenu.js",
        "js/app/bindings/copywidth.js",
        "js/app/bindings/invisible.js",
        "js/app/bindings/popover.js",
        "js/app/bindings/qrcode.js",
        "js/app/bindings/slimscrolledforeach.js",
        "js/app/bindings/toggle.js",
        "js/app/bindings/togglecontent.js",
        "js/app/bindings/valuewithinit.js",
        "js/app/viewmodels/access.js",
        "js/app/viewmodels/appearance.js",
        "js/app/viewmodels/connection.js",
        "js/app/viewmodels/control.js",
        "js/app/viewmodels/files.js",
        "js/app/viewmodels/loginstate.js",
        "js/app/viewmodels/loginui.js",
        "js/app/viewmodels/navigation.js",
        "js/app/viewmodels/printerstate.js",
        "js/app/viewmodels/printerprofiles.js",
        "js/app/viewmodels/settings.js",
        "js/app/viewmodels/slicing.js",
        "js/app/viewmodels/system.js",
        "js/app/viewmodels/temperature.js",
        "js/app/viewmodels/terminal.js",
        "js/app/viewmodels/timelapse.js",
        "js/app/viewmodels/uistate.js",
        "js/app/viewmodels/users.js",
        "js/app/viewmodels/usersettings.js",
        "js/app/viewmodels/wizard.js",
        "js/app/viewmodels/about.js",
    ]

    assets["clientjs"] = [
        "js/app/client/base.js",
        "js/app/client/socket.js",
        "js/app/client/access.js",
        "js/app/client/browser.js",
        "js/app/client/connection.js",
        "js/app/client/control.js",
        "js/app/client/files.js",
        "js/app/client/job.js",
        "js/app/client/languages.js",
        "js/app/client/printer.js",
        "js/app/client/printerprofiles.js",
        "js/app/client/settings.js",
        "js/app/client/slicing.js",
        "js/app/client/system.js",
        "js/app/client/timelapse.js",
        "js/app/client/users.js",
        "js/app/client/util.js",
        "js/app/client/wizard.js",
    ]

    if preferred_stylesheet == "less":
        assets["less"].append("less/octoprint.less")
    elif preferred_stylesheet == "css":
        assets["css"].append("css/octoprint.css")

    return assets


##~~ plugin assets collector


def collect_plugin_assets(preferred_stylesheet="css"):
    logger = logging.getLogger(__name__ + ".collect_plugin_assets")

    supported_stylesheets = ("css", "less")
    assets = {
        "bundled": {
            "js": DefaultOrderedDict(list),
            "clientjs": DefaultOrderedDict(list),
            "css": DefaultOrderedDict(list),
            "less": DefaultOrderedDict(list),
        },
        "external": {
            "js": DefaultOrderedDict(list),
            "clientjs": DefaultOrderedDict(list),
            "css": DefaultOrderedDict(list),
            "less": DefaultOrderedDict(list),
        },
    }

    asset_plugins = octoprint.plugin.plugin_manager().get_implementations(
        octoprint.plugin.AssetPlugin
    )
    for implementation in asset_plugins:
        name = implementation._identifier
        is_bundled = implementation._plugin_info.bundled

        asset_key = "bundled" if is_bundled else "external"

        try:
            all_assets = implementation.get_assets()
            basefolder = implementation.get_asset_folder()
        except Exception:
            logger.exception(
                "Got an error while trying to collect assets from {}, ignoring assets from the plugin".format(
                    name
                ),
                extra={"plugin": name},
            )
            continue

        def asset_exists(category, asset):
            exists = os.path.exists(os.path.join(basefolder, asset))
            if not exists:
                logger.warning(
                    "Plugin {} is referring to non existing {} asset {}".format(
                        name, category, asset
                    )
                )
            return exists

        if "js" in all_assets:
            for asset in all_assets["js"]:
                if not asset_exists("js", asset):
                    continue
                assets[asset_key]["js"][name].append(
                    "plugin/{name}/{asset}".format(**locals())
                )

        if "clientjs" in all_assets:
            for asset in all_assets["clientjs"]:
                if not asset_exists("clientjs", asset):
                    continue
                assets[asset_key]["clientjs"][name].append(
                    "plugin/{name}/{asset}".format(**locals())
                )

        if preferred_stylesheet in all_assets:
            for asset in all_assets[preferred_stylesheet]:
                if not asset_exists(preferred_stylesheet, asset):
                    continue
                assets[asset_key][preferred_stylesheet][name].append(
                    "plugin/{name}/{asset}".format(**locals())
                )
        else:
            for stylesheet in supported_stylesheets:
                if stylesheet not in all_assets:
                    continue

                for asset in all_assets[stylesheet]:
                    if not asset_exists(stylesheet, asset):
                        continue
                    assets[asset_key][stylesheet][name].append(
                        "plugin/{name}/{asset}".format(**locals())
                    )
                break

    return assets


##~~ JSON encoding


class OctoPrintJsonEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        try:
            return JsonEncoding.encode(obj)
        except TypeError:
            return flask.json.JSONEncoder.default(self, obj)
