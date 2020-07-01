# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os
import datetime
import io

from past.builtins import basestring

from collections import defaultdict
from flask import request, g, url_for, make_response, render_template, send_from_directory, redirect, abort, Response

import octoprint.plugin

from octoprint.server import app, userManager, groupManager, pluginManager, gettext, \
	debug, LOCALES, VERSION, DISPLAY_VERSION, BRANCH, preemptiveCache, \
	NOT_MODIFIED
from octoprint.access.permissions import Permissions
from octoprint.settings import settings
from octoprint.filemanager import full_extension_tree, get_all_extensions
from octoprint.util import to_unicode, to_bytes, sv
from octoprint.util.version import get_python_version_string

import re
import base64

from . import util

import logging
_logger = logging.getLogger(__name__)

_templates = dict()
_plugin_names = None
_plugin_vars = None

_valid_id_re = re.compile("[a-z_]+")
_valid_div_re = re.compile("[a-zA-Z_-]+")

def _preemptive_unless(base_url=None, additional_unless=None):
	if base_url is None:
		base_url = request.url_root

	disabled_for_root = not settings().getBoolean(["devel", "cache", "preemptive"]) \
	                    or base_url in settings().get(["server", "preemptiveCache", "exceptions"]) \
	                    or not (base_url.startswith("http://") or base_url.startswith("https://"))

	recording_disabled = request.headers.get("X-Preemptive-Record", "yes") == "no"

	if callable(additional_unless):
		return recording_disabled or disabled_for_root or additional_unless()
	else:
		return recording_disabled or disabled_for_root

def _preemptive_data(key, path=None, base_url=None, data=None, additional_request_data=None):
	if path is None:
		path = request.path
	if base_url is None:
		base_url = request.url_root

	d = dict(path=path,
	         base_url=base_url,
	         query_string="l10n={}".format(g.locale.language if g.locale else "en"))

	if key != "_default":
		d["plugin"] = key

	# add data if we have any
	if data is not None:
		try:
			if callable(data):
				data = data()
			if data:
				if "query_string" in data:
					data["query_string"] = "l10n={}&{}".format(g.locale.language, data["query_string"])
				d.update(data)
		except Exception:
			_logger.exception("Error collecting data for preemptive cache from plugin {}".format(key))

	# add additional request data if we have any
	if callable(additional_request_data):
		try:
			ard = additional_request_data()
			if ard:
				d.update(dict(
					_additional_request_data=ard
				))
		except Exception:
			_logger.exception("Error retrieving additional data for preemptive cache from plugin {}".format(key))

	return d

def _cache_key(ui, url=None, locale=None, additional_key_data=None):
	if url is None:
		url = request.base_url
	if locale is None:
		locale = g.locale.language if g.locale else "en"

	k = "ui:{}:{}:{}".format(ui, url, locale)
	if callable(additional_key_data):
		try:
			ak = additional_key_data()
			if ak:
				# we have some additional key components, let's attach them
				if not isinstance(ak, (list, tuple)):
					ak = [ak]
				k = "{}:{}".format(k, ":".join(ak))
		except Exception:
			_logger.exception("Error while trying to retrieve additional cache key parts for ui {}".format(ui))
	return k

def _valid_status_for_cache(status_code):
	return 200 <= status_code < 400

@app.route("/cached.gif")
def in_cache():
	url = request.base_url.replace("/cached.gif", "/")
	path = request.path.replace("/cached.gif", "/")
	base_url = request.url_root

	# select view from plugins and fall back on default view if no plugin will handle it
	ui_plugins = pluginManager.get_implementations(octoprint.plugin.UiPlugin,
	                                               sorting_context="UiPlugin.on_ui_render")
	for plugin in ui_plugins:
		try:
			if plugin.will_handle_ui(request):
				ui = plugin._identifier
				key = _cache_key(plugin._identifier,
				                 url=url,
				                 additional_key_data=plugin.get_ui_additional_key_data_for_cache)
				unless = _preemptive_unless(url, additional_unless=plugin.get_ui_preemptive_caching_additional_unless)
				data = _preemptive_data(plugin._identifier,
				                        path=path,
				                        base_url=base_url,
				                        data=plugin.get_ui_data_for_preemptive_caching,
				                        additional_request_data=plugin.get_ui_additional_request_data_for_preemptive_caching)
				break
		except Exception:
			_logger.exception("Error while calling plugin {}, skipping it".format(plugin._identifier),
			                  extra=dict(plugin=plugin._identifier))
	else:
		ui = "_default"
		key = _cache_key("_default", url=url)
		unless = _preemptive_unless(url)
		data = _preemptive_data("_default", path=path, base_url=base_url)

	response = make_response(bytes(base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")))
	response.headers["Content-Type"] = "image/gif"

	if unless or not preemptiveCache.has_record(data, root=path):
		_logger.info("Preemptive cache not active for path {}, ui {} and data {!r}, signaling as cached".format(path, ui, data))
		return response
	elif util.flask.is_in_cache(key):
		_logger.info("Found path {} in cache (key: {}), signaling as cached".format(path, key))
		return response
	elif util.flask.is_cache_bypassed(key):
		_logger.info("Path {} was bypassed from cache (key: {}), signaling as cached".format(path, key))
		return response
	else:
		_logger.debug("Path {} not yet cached (key: {}), signaling as missing".format(path, key))
		return abort(404)

@app.route("/")
def index():
	from octoprint.server import printer

	global _templates, _plugin_names, _plugin_vars

	preemptive_cache_enabled = settings().getBoolean(["devel", "cache", "preemptive"])

	locale = g.locale.language if g.locale else "en"

	# helper to check if wizards are active
	def wizard_active(templates):
		return templates is not None and bool(templates["wizard"]["order"])

	# we force a refresh if the client forces one and we are not printing or if we have wizards cached
	client_refresh = util.flask.cache_check_headers()
	request_refresh = "_refresh" in request.values
	printing = printer.is_printing()
	if client_refresh and printing:
		logging.getLogger(__name__).warning("Client requested cache refresh via cache-control headers but we are printing. "
		                                    "Not invalidating caches due to resource limitation. Append ?_refresh=true to "
		                                    "the URL if you absolutely require a refresh now")
	client_refresh = client_refresh and not printing
	force_refresh = client_refresh \
	                or request_refresh \
	                or wizard_active(_templates.get(locale))

	# if we need to refresh our template cache or it's not yet set, process it
	fetch_template_data(refresh=force_refresh)

	now = datetime.datetime.utcnow()

	enable_accesscontrol = userManager.enabled
	enable_timelapse = settings().getBoolean(["webcam", "timelapseEnabled"])
	enable_loading_animation = settings().getBoolean(["devel", "showLoadingAnimation"])
	enable_sd_support = settings().get(["feature", "sdSupport"])
	enable_webcam = settings().getBoolean(["webcam", "webcamEnabled"]) and bool(settings().get(["webcam", "stream"]))
	enable_temperature_graph = settings().get(["feature", "temperatureGraph"])
	sockjs_connect_timeout = settings().getInt(["devel", "sockJsConnectTimeout"])

	def default_template_filter(template_type, template_key):
		if template_type == "navbar":
			return template_key != "login" or enable_accesscontrol
		elif template_type == "tab":
			return (template_key != "timelapse" or enable_timelapse)
		elif template_type == "settings":
			return template_key != "accesscontrol" or enable_accesscontrol
		elif template_type == "usersettings":
			return enable_accesscontrol
		else:
			return True

	default_additional_etag = [enable_accesscontrol,
	                           enable_timelapse,
	                           enable_loading_animation,
	                           enable_sd_support,
	                           enable_webcam,
	                           enable_temperature_graph,
	                           sockjs_connect_timeout,
	                           wizard_active(_templates.get(locale))] + sorted(["{}:{}".format(to_unicode(k, errors="replace"),
	                                                                                           to_unicode(v, errors="replace"))
	                                                                           for k, v in _plugin_vars.items()])

	def get_preemptively_cached_view(key, view, data=None, additional_request_data=None, additional_unless=None):
		if (data is None and additional_request_data is None) or g.locale is None:
			return view

		d = _preemptive_data(key, data=data, additional_request_data=additional_request_data)

		def unless():
			return _preemptive_unless(base_url=request.url_root, additional_unless=additional_unless)

		# finally decorate our view
		return util.flask.preemptively_cached(cache=preemptiveCache,
		                                      data=d,
		                                      unless=unless)(view)

	def get_cached_view(key, view, additional_key_data=None, additional_files=None, additional_etag=None, custom_files=None, custom_etag=None, custom_lastmodified=None):
		if additional_etag is None:
			additional_etag = []

		def cache_key():
			return _cache_key(key, additional_key_data=additional_key_data)

		def collect_files():
			if callable(custom_files):
				try:
					files = custom_files()
					if files:
						return files
				except Exception:
					_logger.exception("Error while trying to retrieve tracked files for plugin {}".format(key))

			files = _get_all_templates()
			files += _get_all_assets()
			files += _get_all_translationfiles(g.locale.language if g.locale else "en",
			                                         "messages")

			if callable(additional_files):
				try:
					af = additional_files()
					if af:
						files += af
				except Exception:
					_logger.exception("Error while trying to retrieve additional tracked files for plugin {}".format(key))

			return sorted(set(files))

		def compute_lastmodified(files):
			if callable(custom_lastmodified):
				try:
					lastmodified = custom_lastmodified()
					if lastmodified:
						return lastmodified
				except Exception:
					_logger.exception("Error while trying to retrieve custom LastModified value for plugin {}".format(key))

			return _compute_date(files)

		def compute_etag(files, lastmodified, additional=None):
			if callable(custom_etag):
				try:
					etag = custom_etag()
					if etag:
						return etag
				except Exception:
					_logger.exception("Error while trying to retrieve custom ETag value for plugin {}".format(key))

			if lastmodified and not isinstance(lastmodified, basestring):
				from werkzeug.http import http_date
				lastmodified = http_date(lastmodified)
			if additional is None:
				additional = []

			import hashlib
			hash = hashlib.sha1()
			def hash_update(value):
				hash.update(to_bytes(value, encoding="utf-8", errors="replace"))
			hash_update(octoprint.__version__)
			hash_update(get_python_version_string())
			hash_update(",".join(sorted(files)))
			if lastmodified:
				hash_update(lastmodified)
			for add in additional:
				hash_update(add)
			return hash.hexdigest()

		current_files = collect_files()
		current_lastmodified = compute_lastmodified(current_files)
		current_etag = compute_etag(files=current_files, lastmodified=current_lastmodified,
			                        additional=[cache_key()] + additional_etag)

		def check_etag_and_lastmodified():
			lastmodified_ok = util.flask.check_lastmodified(current_lastmodified)
			etag_ok = util.flask.check_etag(current_etag)
			return lastmodified_ok and etag_ok

		def validate_cache(cached):
			return force_refresh or (current_etag != cached.get_etag()[0])

		decorated_view = view
		decorated_view = util.flask.lastmodified(lambda _: current_lastmodified)(decorated_view)
		decorated_view = util.flask.etagged(lambda _: current_etag)(decorated_view)
		decorated_view = util.flask.cached(timeout=-1,
		                                   refreshif=validate_cache,
		                                   key=cache_key,
		                                   unless_response=lambda response: util.flask.cache_check_response_headers(response) or util.flask.cache_check_status_code(response, _valid_status_for_cache))(decorated_view)
		decorated_view = util.flask.with_client_revalidation(decorated_view)
		decorated_view = util.flask.conditional(check_etag_and_lastmodified, NOT_MODIFIED)(decorated_view)
		return decorated_view

	def plugin_view(p):
		cached = get_cached_view(p._identifier,
		                         p.on_ui_render,
		                         additional_key_data=p.get_ui_additional_key_data_for_cache,
		                         additional_files=p.get_ui_additional_tracked_files,
		                         custom_files=p.get_ui_custom_tracked_files,
		                         custom_etag=p.get_ui_custom_etag,
		                         custom_lastmodified=p.get_ui_custom_lastmodified,
		                         additional_etag=p.get_ui_additional_etag(default_additional_etag))

		if preemptive_cache_enabled and p.get_ui_preemptive_caching_enabled():
			view = get_preemptively_cached_view(p._identifier,
			                                    cached,
			                                    p.get_ui_data_for_preemptive_caching,
			                                    p.get_ui_additional_request_data_for_preemptive_caching,
			                                    p.get_ui_preemptive_caching_additional_unless)
		else:
			view = cached

		template_filter = p.get_ui_custom_template_filter(default_template_filter)
		if template_filter is not None and callable(template_filter):
			filtered_templates = _filter_templates(_templates[locale], template_filter)
		else:
			filtered_templates = _templates[locale]

		render_kwargs = _get_render_kwargs(filtered_templates,
		                                   _plugin_names,
		                                   _plugin_vars,
		                                   now)

		return view(now, request, render_kwargs)

	def default_view():
		filtered_templates = _filter_templates(_templates[locale], default_template_filter)

		wizard = wizard_active(filtered_templates)
		accesscontrol_active = enable_accesscontrol and userManager.has_been_customized()

		render_kwargs = _get_render_kwargs(filtered_templates,
		                                   _plugin_names,
		                                   _plugin_vars,
		                                   now)
		render_kwargs.update(dict(
			enableWebcam=enable_webcam,
			enableTemperatureGraph=enable_temperature_graph,
			enableAccessControl=enable_accesscontrol,
			accessControlActive=accesscontrol_active,
			enableLoadingAnimation=enable_loading_animation,
			enableSdSupport=enable_sd_support,
			sockJsConnectTimeout=sockjs_connect_timeout * 1000,
			wizard=wizard,
			now=now,
		))

		# no plugin took an interest, we'll use the default UI
		def make_default_ui():
			r = make_response(render_template("index.jinja2", **render_kwargs))
			if wizard:
				# if we have active wizard dialogs, set non caching headers
				r = util.flask.add_non_caching_response_headers(r)
			return r

		cached = get_cached_view("_default",
		                         make_default_ui,
		                         additional_etag=default_additional_etag)
		preemptively_cached = get_preemptively_cached_view("_default",
		                                                   cached,
		                                                   dict(),
		                                                   dict())
		return preemptively_cached()

	response = None

	forced_view = request.headers.get("X-Force-View", None)

	if forced_view:
		# we have view forced by the preemptive cache
		_logger.debug("Forcing rendering of view {}".format(forced_view))
		if forced_view != "_default":
			plugin = pluginManager.get_plugin_info(forced_view, require_enabled=True)
			if plugin is not None and isinstance(plugin.implementation, octoprint.plugin.UiPlugin):
				response = plugin_view(plugin.implementation)
				if _logger.isEnabledFor(logging.DEBUG) and isinstance(response, Response):
					response.headers["X-Ui-Plugin"] = plugin._identifier
		else:
			response = default_view()
			if _logger.isEnabledFor(logging.DEBUG) and isinstance(response, Response):
				response.headers["X-Ui-Plugin"] = "_default"

	else:
		# select view from plugins and fall back on default view if no plugin will handle it
		ui_plugins = pluginManager.get_implementations(octoprint.plugin.UiPlugin, sorting_context="UiPlugin.on_ui_render")
		for plugin in ui_plugins:
			try:
				if plugin.will_handle_ui(request):
					# plugin claims responsibility, let it render the UI
					response = plugin_view(plugin)
					if response is not None:
						if _logger.isEnabledFor(logging.DEBUG) and isinstance(response, Response):
							response.headers["X-Ui-Plugin"] = plugin._identifier
						break
					else:
						_logger.warning("UiPlugin {} returned an empty response".format(plugin._identifier))
			except Exception:
				_logger.exception("Error while calling plugin {}, skipping it".format(plugin._identifier),
				                  extra=dict(plugin=plugin._identifier))
		else:
			response = default_view()
			if _logger.isEnabledFor(logging.DEBUG) and isinstance(response, Response):
				response.headers["X-Ui-Plugin"] = "_default"

	if response is None:
		return abort(404)
	return response


def _get_render_kwargs(templates, plugin_names, plugin_vars, now):
	global _logger

	#~~ a bunch of settings

	first_run = settings().getBoolean(["server", "firstRun"])

	locales = dict()
	for l in LOCALES:
		try:
			locales[l.language] = dict(language=l.language, display=l.display_name, english=l.english_name)
		except Exception:
			_logger.exception("Error while collecting available locales")

	permissions = [permission.as_dict() for permission in Permissions.all()]
	filetypes = list(sorted(full_extension_tree().keys()))
	extensions = list(map(lambda ext: ".{}".format(ext), get_all_extensions()))

	#~~ prepare full set of template vars for rendering

	render_kwargs = dict(
		debug=debug,
		firstRun=first_run,
		version=dict(number=VERSION, display=DISPLAY_VERSION, branch=BRANCH),
		python_version=get_python_version_string(),
		templates=templates,
		pluginNames=plugin_names,
		locales=locales,
		permissions=permissions,
		supportedFiletypes=filetypes,
		supportedExtensions=extensions
	)
	render_kwargs.update(plugin_vars)

	return render_kwargs


def fetch_template_data(refresh=False):
	global _templates, _plugin_names, _plugin_vars

	locale = g.locale.language if g.locale else "en"

	if not refresh and _templates.get(locale) is not None and _plugin_names is not None and _plugin_vars is not None:
		return _templates[locale], _plugin_names, _plugin_vars

	first_run = settings().getBoolean(["server", "firstRun"])

	##~~ prepare templates

	templates = defaultdict(lambda: dict(order=[], entries=dict()))

	# rules for transforming template configs to template entries
	template_rules = dict(
		navbar=dict(div=lambda x: "navbar_plugin_" + x, template=lambda x: x + "_navbar.jinja2", to_entry=lambda data: data),
		sidebar=dict(div=lambda x: "sidebar_plugin_" + x, template=lambda x: x + "_sidebar.jinja2", to_entry=lambda data: (data["name"], data)),
		tab=dict(div=lambda x: "tab_plugin_" + x, template=lambda x: x + "_tab.jinja2", to_entry=lambda data: (data["name"], data)),
		settings=dict(div=lambda x: "settings_plugin_" + x, template=lambda x: x + "_settings.jinja2", to_entry=lambda data: (data["name"], data)),
		usersettings=dict(div=lambda x: "usersettings_plugin_" + x, template=lambda x: x + "_usersettings.jinja2", to_entry=lambda data: (data["name"], data)),
		wizard=dict(div=lambda x: "wizard_plugin_" + x, template=lambda x: x + "_wizard.jinja2", to_entry=lambda data: (data["name"], data)),
		about=dict(div=lambda x: "about_plugin_" + x, template=lambda x: x + "_about.jinja2", to_entry=lambda data: (data["name"], data)),
		generic=dict(template=lambda x: x + ".jinja2", to_entry=lambda data: data)
	)

	# sorting orders
	def wizard_key_extractor(d, k):
		if d[1].get("_key", None) == "plugin_corewizard_acl":
			# Ultra special case - we MUST always have the ACL wizard first since otherwise any steps that follow and
			# that require to access APIs to function will run into errors since those APIs won't work before ACL
			# has been configured. See also #2140
			return "0:{}".format(to_unicode(d[0]))
		elif d[1].get("mandatory", False):
			# Other mandatory steps come before the optional ones
			return "1:{}".format(to_unicode(d[0]))
		else:
			# Finally everything else
			return "2:{}".format(to_unicode(d[0]))

	template_sorting = dict(
		navbar=dict(add="prepend", key=None),
		sidebar=dict(add="append", key="name"),
		tab=dict(add="append", key="name"),
		settings=dict(add="custom_append", key="name", custom_add_entries=lambda missing: dict(section_plugins=(gettext("Plugins"), None)), custom_add_order=lambda missing: ["section_plugins"] + missing),
		usersettings=dict(add="append", key="name"),
		wizard=dict(add="append", key="name", key_extractor=wizard_key_extractor),
		about=dict(add="append", key="name"),
		generic=dict(add="append", key=None)
	)

	hooks = pluginManager.get_hooks("octoprint.ui.web.templatetypes")
	for name, hook in hooks.items():
		try:
			result = hook(dict(template_sorting), dict(template_rules))
		except Exception:
			_logger.exception("Error while retrieving custom template type "
			                  "definitions from plugin {name}".format(**locals()),
			                  extra=dict(plugin=name))
		else:
			if not isinstance(result, list):
				continue

			for entry in result:
				if not isinstance(entry, tuple) or not len(entry) == 3:
					continue

				key, order, rule = entry

				# order defaults
				if "add" not in order:
					order["add"] = "prepend"
				if "key" not in order:
					order["key"] = "name"

				# rule defaults
				if "div" not in rule:
					# default div name: <hook plugin>_<template_key>_plugin_<plugin>
					div = "{name}_{key}_plugin_".format(**locals())
					rule["div"] = lambda x: div + x
				if "template" not in rule:
					# default template name: <plugin>_plugin_<hook plugin>_<template key>.jinja2
					template = "_plugin_{name}_{key}.jinja2".format(**locals())
					rule["template"] = lambda x: x + template
				if "to_entry" not in rule:
					# default to_entry assumes existing "name" property to be used as label for 2-tuple entry data structure (<name>, <properties>)
					rule["to_entry"] = lambda data: (data["name"], data)

				template_rules["plugin_" + name + "_" + key] = rule
				template_sorting["plugin_" + name + "_" + key] = order
	template_types = list(template_rules.keys())

	# navbar

	templates["navbar"]["entries"] = dict(
		settings=dict(template="navbar/settings.jinja2", _div="navbar_settings", styles=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.SETTINGS)"),
		systemmenu=dict(template="navbar/systemmenu.jinja2", _div="navbar_systemmenu", classes=["dropdown"], styles=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.SYSTEM)", custom_bindings=False),
		login=dict(template="navbar/login.jinja2", _div="navbar_login", classes=["dropdown"], custom_bindings=False),
	)

	# sidebar

	templates["sidebar"]["entries"]= dict(
		connection=(gettext("Connection"), dict(template="sidebar/connection.jinja2", _div="connection", icon="signal", styles_wrapper=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.CONNECTION)", template_header="sidebar/connection_header.jinja2")),
		state=(gettext("State"), dict(template="sidebar/state.jinja2", _div="state", icon="info-circle", styles_wrapper=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.STATUS)")),
		files=(gettext("Files"), dict(template="sidebar/files.jinja2", _div="files", icon="list", classes_content=["overflow_visible"], template_header="sidebar/files_header.jinja2", styles_wrapper=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.FILES_LIST)"))
	)

	# tabs

	templates["tab"]["entries"] = dict(
		temperature=(gettext("Temperature"), dict(template="tabs/temperature.jinja2", _div="temp", styles=["display: none;"], data_bind="visible: loginState.hasAnyPermissionKo(access.permissions.STATUS, access.permissions.CONTROL)() && visible()")),
		control=(gettext("Control"), dict(template="tabs/control.jinja2", _div="control", styles=["display: none;"], data_bind="visible: loginState.hasAnyPermissionKo(access.permissions.WEBCAM, access.permissions.CONTROL)")),
		terminal=(gettext("Terminal"), dict(template="tabs/terminal.jinja2", _div="term", styles=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.MONITOR_TERMINAL)")),
		timelapse=(gettext("Timelapse"), dict(template="tabs/timelapse.jinja2", _div="timelapse", styles=["display: none;"], data_bind="visible: loginState.hasPermissionKo(access.permissions.TIMELAPSE_LIST)"))
	)

	# settings dialog

	templates["settings"]["entries"] = dict(
		section_printer=(gettext("Printer"), None),

		serial=(gettext("Serial Connection"), dict(template="dialogs/settings/serialconnection.jinja2", _div="settings_serialConnection", custom_bindings=False)),
		printerprofiles=(gettext("Printer Profiles"), dict(template="dialogs/settings/printerprofiles.jinja2", _div="settings_printerProfiles", custom_bindings=False)),
		temperatures=(gettext("Temperatures"), dict(template="dialogs/settings/temperatures.jinja2", _div="settings_temperature", custom_bindings=False)),
		terminalfilters=(gettext("Terminal Filters"), dict(template="dialogs/settings/terminalfilters.jinja2", _div="settings_terminalFilters", custom_bindings=False)),
		gcodescripts=(gettext("GCODE Scripts"), dict(template="dialogs/settings/gcodescripts.jinja2", _div="settings_gcodeScripts", custom_bindings=False)),

		section_features=(gettext("Features"), None),

		features=(gettext("Features"), dict(template="dialogs/settings/features.jinja2", _div="settings_features", custom_bindings=False)),
		webcam=(gettext("Webcam & Timelapse"), dict(template="dialogs/settings/webcam.jinja2", _div="settings_webcam", custom_bindings=False)),
		api=(gettext("API"), dict(template="dialogs/settings/api.jinja2", _div="settings_api", custom_bindings=False)),

		section_octoprint=(gettext("OctoPrint"), None),

		accesscontrol=(gettext("Access Control"), dict(template="dialogs/settings/accesscontrol.jinja2", _div="settings_users", custom_bindings=False)),
		folders=(gettext("Folders"), dict(template="dialogs/settings/folders.jinja2", _div="settings_folders", custom_bindings=False)),
		appearance=(gettext("Appearance"), dict(template="dialogs/settings/appearance.jinja2", _div="settings_appearance", custom_bindings=False)),
		server=(gettext("Server"), dict(template="dialogs/settings/server.jinja2", _div="settings_server", custom_bindings=False)),
	)

	# user settings dialog

	templates["usersettings"]["entries"] = dict(
		access=(gettext("Access"), dict(template="dialogs/usersettings/access.jinja2", _div="usersettings_access", custom_bindings=False)),
		interface=(gettext("Interface"), dict(template="dialogs/usersettings/interface.jinja2", _div="usersettings_interface", custom_bindings=False)),
	)

	# wizard

	if first_run:
		def custom_insert_order(existing, missing):
			if "firstrunstart" in missing:
				missing.remove("firstrunstart")
			if "firstrunend" in missing:
				missing.remove("firstrunend")

			return ["firstrunstart"] + existing + missing + ["firstrunend"]

		template_sorting["wizard"].update(dict(add="custom_insert", custom_insert_entries=lambda missing: dict(), custom_insert_order=custom_insert_order))
		templates["wizard"]["entries"] = dict(
			firstrunstart=(gettext("Start"), dict(template="dialogs/wizard/firstrun_start.jinja2", _div="wizard_firstrun_start")),
			firstrunend=(gettext("Finish"), dict(template="dialogs/wizard/firstrun_end.jinja2", _div="wizard_firstrun_end")),
		)

	# about dialog

	templates["about"]["entries"] = dict(
		about=("About OctoPrint", dict(template="dialogs/about/about.jinja2", _div="about_about", custom_bindings=False)),
		license=("OctoPrint License", dict(template="dialogs/about/license.jinja2", _div="about_license", custom_bindings=False)),
		thirdparty=("Third Party Licenses", dict(template="dialogs/about/thirdparty.jinja2", _div="about_thirdparty", custom_bindings=False)),
		authors=("Authors", dict(template="dialogs/about/authors.jinja2", _div="about_authors", custom_bindings=False)),
		supporters=("Supporters", dict(template="dialogs/about/supporters.jinja2", _div="about_sponsors", custom_bindings=False))
	)

	# extract data from template plugins

	template_plugins = pluginManager.get_implementations(octoprint.plugin.TemplatePlugin)

	plugin_vars = dict()
	plugin_names = set()
	plugin_aliases = dict()
	seen_wizards = settings().get(["server", "seenWizards"]) if not first_run else dict()
	for implementation in template_plugins:
		name = implementation._identifier
		plugin_names.add(name)
		wizard_required = False
		wizard_ignored = False

		try:
			vars = implementation.get_template_vars()
			configs = implementation.get_template_configs()
			if isinstance(implementation, octoprint.plugin.WizardPlugin):
				wizard_required = implementation.is_wizard_required()
				wizard_ignored = octoprint.plugin.WizardPlugin.is_wizard_ignored(seen_wizards, implementation)
		except Exception:
			_logger.exception("Error while retrieving template data for plugin {}, ignoring it".format(name),
			                  extra=dict(plugin=name))
			continue

		if not isinstance(vars, dict):
			vars = dict()
		if not isinstance(configs, (list, tuple)):
			configs = []

		for var_name, var_value in vars.items():
			plugin_vars["plugin_" + name + "_" + var_name] = var_value

		includes = _process_template_configs(name, implementation, configs, template_rules)

		if not wizard_required or wizard_ignored:
			includes["wizard"] = list()

		for t in template_types:
			plugin_aliases[t] = dict()
			for include in includes[t]:
				if t == "navbar" or t == "generic":
					data = include
				else:
					data = include[1]

				key = data["_key"]
				if "replaces" in data:
					key = data["replaces"]
					plugin_aliases[t][data["_key"]] = data["replaces"]
				templates[t]["entries"][key] = include

	#~~ order internal templates and plugins

	# make sure that
	# 1) we only have keys in our ordered list that we have entries for and
	# 2) we have all entries located somewhere within the order

	for t in template_types:
		default_order = settings().get(["appearance", "components", "order", t], merged=True, config=dict()) or []
		configured_order = settings().get(["appearance", "components", "order", t], merged=True) or []
		configured_disabled = settings().get(["appearance", "components", "disabled", t]) or []

		# first create the ordered list of all component ids according to the configured order
		result = []
		for x in configured_order:
			if x in plugin_aliases[t]:
				x = plugin_aliases[t][x]
			if x in templates[t]["entries"] and not x in configured_disabled and not x in result:
				result.append(x)
		templates[t]["order"] = result

		# now append the entries from the default order that are not already in there
		templates[t]["order"] += [x for x in default_order if not x in templates[t]["order"] and x in templates[t]["entries"] and not x in configured_disabled]

		all_ordered = set(templates[t]["order"])
		all_disabled = set(configured_disabled)

		# check if anything is missing, if not we are done here
		missing_in_order = set(templates[t]["entries"].keys()).difference(all_ordered).difference(all_disabled)
		if len(missing_in_order) == 0:
			continue

		# works with entries that are dicts and entries that are 2-tuples with the
		# entry data at index 1
		def config_extractor(item, key, default_value=None):
			if isinstance(item, dict) and key in item:
				return item[key] if key in item else default_value
			elif isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], dict) and key in item[1]:
				return item[1][key] if key in item[1] else default_value

			return default_value

		# finally add anything that's not included in our order yet
		if template_sorting[t]["key"] is not None:
			# we'll use our config extractor as default key extractor
			extractor = config_extractor

			# if template type provides custom extractor, make sure its exceptions are handled
			if "key_extractor" in template_sorting[t] and callable(template_sorting[t]["key_extractor"]):
				def create_safe_extractor(extractor):
					def f(x, k):
						try:
							return extractor(x, k)
						except Exception:
							_logger.exception("Error while extracting sorting keys for template {}".format(t))
							return None
					return f
				extractor = create_safe_extractor(template_sorting[t]["key_extractor"])

			sort_key = template_sorting[t]["key"]

			def key_func(x):
				config = templates[t]["entries"][x]
				entry_order = config_extractor(config, "order", default_value=None)
				return entry_order is None, sv(entry_order), sv(extractor(config, sort_key))

			sorted_missing = sorted(missing_in_order, key=key_func)
		else:
			def key_func(x):
				config = templates[t]["entries"][x]
				entry_order = config_extractor(config, "order", default_value=None)
				return entry_order is None, sv(entry_order)

			sorted_missing = sorted(missing_in_order, key=key_func)

		if template_sorting[t]["add"] == "prepend":
			templates[t]["order"] = sorted_missing + templates[t]["order"]
		elif template_sorting[t]["add"] == "append":
			templates[t]["order"] += sorted_missing
		elif template_sorting[t]["add"] == "custom_prepend" and "custom_add_entries" in template_sorting[t] and "custom_add_order" in template_sorting[t]:
			templates[t]["entries"].update(template_sorting[t]["custom_add_entries"](sorted_missing))
			templates[t]["order"] = template_sorting[t]["custom_add_order"](sorted_missing) + templates[t]["order"]
		elif template_sorting[t]["add"] == "custom_append" and "custom_add_entries" in template_sorting[t] and "custom_add_order" in template_sorting[t]:
			templates[t]["entries"].update(template_sorting[t]["custom_add_entries"](sorted_missing))
			templates[t]["order"] += template_sorting[t]["custom_add_order"](sorted_missing)
		elif template_sorting[t]["add"] == "custom_insert" and "custom_insert_entries" in template_sorting[t] and "custom_insert_order" in template_sorting[t]:
			templates[t]["entries"].update(template_sorting[t]["custom_insert_entries"](sorted_missing))
			templates[t]["order"] = template_sorting[t]["custom_insert_order"](templates[t]["order"], sorted_missing)

	_templates[locale] = templates
	_plugin_names = plugin_names
	_plugin_vars = plugin_vars

	return templates, plugin_names, plugin_vars


def _process_template_configs(name, implementation, configs, rules):
	from jinja2.exceptions import TemplateNotFound

	counters = defaultdict(lambda: 1)
	includes = defaultdict(list)

	for config in configs:
		if not isinstance(config, dict):
			continue
		if not "type" in config:
			continue

		template_type = config["type"]
		del config["type"]

		if not template_type in rules:
			continue
		rule = rules[template_type]

		data = _process_template_config(name, implementation, rule, config=config, counter=counters[template_type])
		if data is None:
			continue

		includes[template_type].append(rule["to_entry"](data))
		counters[template_type] += 1

	for template_type in rules:
		if len(includes[template_type]) == 0:
			# if no template of that type was added by the config, we'll try to use the default template name
			rule = rules[template_type]
			data = _process_template_config(name, implementation, rule)
			if data is not None:
				try:
					app.jinja_env.get_or_select_template(data["template"])
				except TemplateNotFound:
					pass
				except Exception:
					_logger.exception("Error in template {}, not going to include it".format(data["template"]))
				else:
					includes[template_type].append(rule["to_entry"](data))

	return includes


def _process_template_config(name, implementation, rule, config=None, counter=1):
	if "mandatory" in rule:
		for mandatory in rule["mandatory"]:
			if not mandatory in config:
				return None

	if config is None:
		config = dict()
	data = dict(config)

	if not "suffix" in data and counter > 1:
		data["suffix"] = "_%d" % counter

	if "div" in data:
		data["_div"] = data["div"]
	elif "div" in rule:
		data["_div"] = rule["div"](name)
		if "suffix" in data:
			data["_div"] = data["_div"] + data["suffix"]
		if not _valid_div_re.match(data["_div"]):
			_logger.warning("Template config {} contains invalid div identifier {}, skipping it".format(name, data["_div"]))
			return None

	if not "template" in data:
		data["template"] = rule["template"](name)

	if not "name" in data:
		data["name"] = implementation._plugin_name

	if not "custom_bindings" in data or data["custom_bindings"]:
		data_bind = "allowBindings: true"
		if "data_bind" in data:
			data_bind = data_bind + ", " + data["data_bind"]
		data_bind = data_bind.replace("\"", "\\\"")
		data["data_bind"] = data_bind

	data["_key"] = "plugin_" + name
	if "suffix" in data:
		data["_key"] += data["suffix"]

	data["_plugin"] = name

	return data


def _filter_templates(templates, template_filter):
	filtered_templates = dict()
	for template_type, template_collection in templates.items():
		filtered_entries = dict()
		for template_key, template_entry in template_collection["entries"].items():
			if template_filter(template_type, template_key):
				filtered_entries[template_key] = template_entry
		filtered_templates[template_type] = dict(order=list(filter(lambda x: x in filtered_entries,
		                                                      	   template_collection["order"])),
		                                         entries=filtered_entries)
	return filtered_templates


@app.route("/robots.txt")
def robotsTxt():
	return send_from_directory(app.static_folder, "robots.txt")


@app.route("/i18n/<string:locale>/<string:domain>.js")
@util.flask.conditional(lambda: _check_etag_and_lastmodified_for_i18n(), NOT_MODIFIED)
@util.flask.etagged(lambda _: _compute_etag_for_i18n(request.view_args["locale"], request.view_args["domain"]))
@util.flask.lastmodified(lambda _: _compute_date_for_i18n(request.view_args["locale"], request.view_args["domain"]))
def localeJs(locale, domain):
	messages = dict()
	plural_expr = None

	if locale != "en":
		messages, plural_expr = _get_translations(locale, domain)

	catalog = dict(
		messages=messages,
		plural_expr=plural_expr,
		locale=locale,
		domain=domain
	)

	from flask import Response
	return Response(render_template("i18n.js.jinja2", catalog=catalog), content_type="application/x-javascript; charset=utf-8")


@app.route("/plugin_assets/<string:name>/<path:filename>")
def plugin_assets(name, filename):
	return redirect(url_for("plugin." + name + ".static", filename=filename))


def _compute_etag_for_i18n(locale, domain, files=None, lastmodified=None):
	if files is None:
		files = _get_all_translationfiles(locale, domain)
	if lastmodified is None:
		lastmodified = _compute_date(files)
	if lastmodified and not isinstance(lastmodified, basestring):
		from werkzeug.http import http_date
		lastmodified = http_date(lastmodified)

	import hashlib
	hash = hashlib.sha1()
	def hash_update(value):
		hash.update(value.encode('utf-8'))
	hash_update(",".join(sorted(files)))
	if lastmodified:
		hash_update(lastmodified)
	return hash.hexdigest()


def _compute_date_for_i18n(locale, domain):
	return _compute_date(_get_all_translationfiles(locale, domain))


def _compute_date(files):
	# Note, we do not expect everything in 'files' to exist.
	from datetime import datetime
	import stat
	max_timestamp = 0
	for path in files:
		try:
			# try to stat file. If an exception is thrown, its because it does not exist.
			s = os.stat(path)
			if stat.S_ISREG(s.st_mode) and s.st_mtime > max_timestamp:
				# is a regular file and has a newer timestamp
				max_timestamp = s.st_mtime
		except Exception:
			# path does not exist.
			continue

	if max_timestamp:
		# we set the micros to 0 since microseconds are not speced for HTTP
		max_timestamp = datetime.fromtimestamp(max_timestamp).replace(microsecond=0)
	return max_timestamp


def _check_etag_and_lastmodified_for_i18n():
	locale = request.view_args["locale"]
	domain = request.view_args["domain"]

	etag_ok = util.flask.check_etag(_compute_etag_for_i18n(request.view_args["locale"], request.view_args["domain"]))

	lastmodified = _compute_date_for_i18n(locale, domain)
	lastmodified_ok = lastmodified is None or util.flask.check_lastmodified(lastmodified)

	return etag_ok and lastmodified_ok


def _get_all_templates():
	from octoprint.util.jinja import get_all_template_paths
	return get_all_template_paths(app.jinja_loader)


def _get_all_assets():
	from octoprint.util.jinja import get_all_asset_paths
	return get_all_asset_paths(app.jinja_env.assets_environment, verifyExist=False)


def _get_all_translationfiles(locale, domain):
	from flask import _request_ctx_stack

	def get_po_path(basedir, locale, domain):
		return os.path.join(basedir, locale, "LC_MESSAGES", "{domain}.po".format(**locals()))

	po_files = []

	user_base_path = os.path.join(settings().getBaseFolder("translations", check_writable=False))
	user_plugin_path = os.path.join(user_base_path, "_plugins")

	# plugin translations
	plugins = octoprint.plugin.plugin_manager().enabled_plugins
	for name, plugin in plugins.items():
		dirs = [os.path.join(user_plugin_path, name), os.path.join(plugin.location, 'translations')]
		for dirname in dirs:
			po_files.append(get_po_path(dirname, locale, domain))

	# core translations
	ctx = _request_ctx_stack.top
	base_path = os.path.join(ctx.app.root_path, "translations")

	dirs = [user_base_path, base_path]
	for dirname in dirs:
		po_files.append(get_po_path(dirname, locale, domain))

	return po_files


def _get_translations(locale, domain):
	from babel.messages.pofile import read_po
	from octoprint.util import dict_merge

	messages = dict()
	plural_expr = None

	def messages_from_po(path, locale, domain):
		messages = dict()
		with io.open(path, mode="rt", encoding="utf-8") as f:
			catalog = read_po(f, locale=locale, domain=domain)

			for message in catalog:
				message_id = message.id
				if isinstance(message_id, (list, tuple)):
					message_id = message_id[0]
				if message.string:
					messages[message_id] = message.string

		return messages, catalog.plural_expr

	po_files = _get_all_translationfiles(locale, domain)
	for po_file in po_files:
		if not os.path.exists(po_file):
			continue
		po_messages, plural_expr = messages_from_po(po_file, locale, domain)
		if po_messages is not None:
			messages = dict_merge(messages, po_messages)

	return messages, plural_expr
