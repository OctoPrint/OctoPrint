# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

import octoprint.plugin

from flask_babel import gettext

from octoprint.access.permissions import Permissions

from collections import defaultdict
import threading

class LoginUiPlugin(octoprint.plugin.UiPlugin,
                    octoprint.plugin.TemplatePlugin,
                    octoprint.plugin.AssetPlugin):
	MAX_BACKLOG_LEN = 100

	# noinspection PyMissingConstructor
	def __init__(self):
		self._message_backlog = defaultdict(list)
		self._message_backlog_mutex = threading.RLock()

	@property
	def active(self):
		# we are only active if ACL is enabled AND configured
		return self._user_manager.enabled and self._user_manager.has_been_customized()

	def get_assets(self):
		return dict(
			js=["js/viewmodel.js"]
		)

	def will_handle_ui(self, request):
		if not self.active:
			# not active, not responsible
			return False

		from octoprint.server.util import loginUserFromApiKey, loginUserFromAuthorizationHeader, InvalidApiKeyException
		from octoprint.server.util.flask import passive_login

		# first try to login via api key & authorization header, just in case that's set
		try:
			if loginUserFromApiKey():
				# successful? No need for handling the UI
				return False
		except InvalidApiKeyException:
			pass # ignored

		if loginUserFromAuthorizationHeader():
			# successful? No need for handling the UI
			return False

		# then try a passive login
		passive_login()
		if Permissions.STATUS.can() and Permissions.SETTINGS_READ.can():
			# Status & settings_read permission? No need to handle UI
			return False
		else:
			return True

	def on_ui_render(self, now, request, render_kwargs):
		from flask import render_template, make_response

		def add_additional_assets(hook):
			result = []
			for name, hook in self._plugin_manager.get_hooks(hook).items():
				try:
					assets = hook()
					if isinstance(assets, (tuple, list)):
						result += assets
				except:
					self._logger.exception("Error fetching theming CSS to include from plugin {}".format(name),
					                       extra=dict(plugin=name))
			return result

		additional_assets = []
		additional_assets += add_additional_assets("octoprint.plugin.loginui.theming")

		# backwards compatibility to old forcelogin plugin which was replaced by this one
		additional_assets += add_additional_assets("octoprint.plugin.forcelogin.theming")

		render_kwargs.update(dict(loginui_theming=additional_assets))
		return make_response(render_template("loginui_index.jinja2", **render_kwargs))

	def get_ui_custom_tracked_files(self):
		from os.path import join as opj

		paths = [opj("static", "css", "loginui.css"),
		         opj("static", "js", "main.js"),
		         opj("static", "js", "viewmodel.js"),
		         opj("static", "less", "loginui.less"),
		         opj("templates", "parts", "loginui_css.jinja2"),
		         opj("templates", "parts", "loginui_javascripts.jinja2"),
		         opj("templates", "loginui_index.jinja2")]

		return [opj(self._basefolder, path) for path in paths]

	def get_ui_preemptive_caching_enabled(self):
		return False

	def get_sorting_key(self, context=None):
		if context == "UiPlugin.on_ui_render":
			# If a plugin *really* wants to come before this plugin, it'll have to turn to negative numbers.
			#
			# This is obviously discouraged for security reasons, but very specific setups might make it necessary,
			# so we make it possible. If this should get abused long term we can always turn this into -inf.
			return 0

__plugin_name__ = "Login UI"
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Displays a standalone login UI if needed"
__plugin_disabling_discouraged__ = gettext("Without this plugin there will be no dedicated login page for users in "
                                           "case anonymous read only access is disabled - instead your non logged in "
                                           "visitors will get a broken UI.")
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hidden__ = True

__plugin_implementation__ = LoginUiPlugin()
