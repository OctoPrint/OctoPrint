# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2018 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

import flask
import flask_login
from flask_babel import gettext

from collections import defaultdict
import threading

class ForceLoginPlugin(octoprint.plugin.UiPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.AssetPlugin):
	MAX_BACKLOG_LEN = 100

	# noinspection PyMissingConstructor
	def __init__(self):
		self._message_backlog = defaultdict(list)
		self._message_backlog_mutex = threading.RLock()

	def get_assets(self):
		return dict(
			js=["js/viewmodel.js"]
		)

	def will_handle_ui(self, request):
		if self._user_manager.enabled and not self._user_manager.hasBeenCustomized():
			# ACL hasn't been configured yet, make an exception
			return False

		from octoprint.server.util.flask import passive_login

		result = passive_login()
		if hasattr(result, "status_code") and result.status_code == 200:
			# passive login successful, no need to handle that
			return False
		else:
			return True

	def on_ui_render(self, now, request, render_kwargs):
		from flask import render_template, make_response

		"""
		Support theming of the login dialog, just in case the core UI is themed as well.

		Example usage by a plugin:

		  def forcelogin_theming():
		      from flask import url_for
		      return [url_for("plugin.myplugin.static", filename="css/forcelogin_theme.css")]

		  __plugin_hooks__ = {
		      "octoprint.plugin.forcelogin.theming": forcelogin_theming
		  }

		Only a list of ready-made URLs to CSS files is supported, neither LESS nor JS. Best use
		url_for like in the example above to be prepared for any configured prefix URLs.
		"""
		additional_assets = []
		for name, hook in self._plugin_manager.get_hooks("octoprint.plugin.forcelogin.theming").items():
			try:
				assets = hook()
				if isinstance(assets, (tuple, list)):
					additional_assets += assets
			except:
				self._logger.exception("Error fetching theming CSS to include from plugin {}".format(name))

		render_kwargs.update(dict(forcelogin_theming=additional_assets))
		return make_response(render_template("forcelogin_index.jinja2", **render_kwargs))

	def get_ui_custom_tracked_files(self):
		from os.path import join as opj

		paths = [opj("static", "css", "forcelogin.css"),
		         opj("static", "js", "main.js"),
		         opj("static", "js", "viewmodel.js"),
		         opj("static", "less", "forcelogin.less"),
		         opj("templates", "parts", "forcelogin_css.jinja2"),
		         opj("templates", "parts", "forcelogin_javascripts.jinja2"),
		         opj("templates", "forcelogin_index.jinja2")]

		return [opj(self._basefolder, path) for path in paths]

	def get_ui_preemptive_caching_enabled(self):
		return False

	def get_before_request_handlers(self):
		def check_login_required():
			if self._user_manager.enabled and not self._user_manager.hasBeenCustomized():
				# ACL hasn't been configured yet, make an exception
				return
			elif not self._user_manager.enabled:
				# ACL isn't enabled
				return

			if flask.request.endpoint in ("api.login",):
				return

			user = flask_login.current_user
			if user is None or user.is_anonymous() or not user.is_active():
				return flask.make_response("Forbidden", 403)

		return [check_login_required]

	def access_validator(self, request):
		if self._user_manager.enabled and not self._user_manager.hasBeenCustomized():
			# ACL hasn't been configured yet, make an exception
			return
		elif not self._user_manager.enabled:
			# ACL isn't enabled
			return

		import tornado.web
		from octoprint.server.util.flask import get_flask_user_from_request

		user = get_flask_user_from_request(request)
		if user is None or not user.is_authenticated():
			raise tornado.web.HTTPError(403)

	def socket_register_validator(self, socket, user):
		if self._user_manager.enabled and not self._user_manager.hasBeenCustomized():
			# ACL hasn't been configured yet, make an exception
			return True
		elif not self._user_manager.enabled:
			# ACL isn't enabled
			return True

		return user is not None and not user.is_anonymous() and user.is_active()

	def socket_authed(self, socket, user):
		with self._message_backlog_mutex:
			backlog = self._message_backlog.pop(socket, [])

		if len(backlog):
			for message, payload in backlog:
				socket._do_emit(message, payload)
			self._logger.debug("Sent backlog of {} message(s) via socket".format(len(backlog)))

	def socket_emit_validator(self, socket, user, message, payload):
		if self._user_manager.enabled and not self._user_manager.hasBeenCustomized():
			# ACL hasn't been configured yet, make an exception
			return True
		elif not self._user_manager.enabled:
			# ACL isn't enabled
			return True

		if message in ("connected", "reauthRequired"):
			return True

		if user is not None and not user.is_anonymous() and user.is_active():
			return True

		with self._message_backlog_mutex:
			if len(self._message_backlog[socket]) < self.MAX_BACKLOG_LEN:
				self._message_backlog[socket].append((message, payload))
				self._logger.debug("Socket message held back until authed, added to backlog: {}".format(message))
			else:
				self._logger.warn("Socket message held back, but backlog full. Throwing message away: {}".format(message))

		return False


__plugin_name__ = "Force Login"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Forces users to login, disables read-only mode."
__plugin_disabling_discouraged__ = gettext("Without this plugin anonymous users will have read-only access to your "
                                           "OctoPrint instance. Only disable this if you are comfortable with this, your "
                                           "OctoPrint instance is not publicly reachable on the internet and you fully "
                                           "trust everyone who has access to your local network!")

__plugin_implementation__ = ForceLoginPlugin()
__plugin_hooks__ = {
	"octoprint.server.api.before_request": __plugin_implementation__.get_before_request_handlers,
	"octoprint.server.http.access_validator": __plugin_implementation__.access_validator,
	"octoprint.server.sockjs.register": __plugin_implementation__.socket_register_validator,
	"octoprint.server.sockjs.authed": __plugin_implementation__.socket_authed,
	"octoprint.server.sockjs.emit": __plugin_implementation__.socket_emit_validator
}
