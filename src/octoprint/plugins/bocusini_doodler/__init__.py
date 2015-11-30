# coding=utf-8
from __future__ import absolute_import

__author__ = "Print2Taste <info@print2taste.de>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 Print2taste Project - Released under terms of the AGPLv3 License"

from werkzeug import secure_filename
import flask

import octoprint.plugin

from octoprint.server.util.flask import restricted_access
from octoprint.server import admin_permission
import octoprint.settings


##~~ Plugin
class BocusiniDoodlerPlugin(octoprint.plugin.BlueprintPlugin,
                           octoprint.plugin.SettingsPlugin,
                           octoprint.plugin.AssetPlugin,
                           octoprint.plugin.TemplatePlugin,
						   octoprint.plugin.StartupPlugin):
	def __init__(self):
		pass

	def on_after_startup(self):
		import os
		self.thumbs_folder = os.path.join(self._settings.global_get_basefolder("uploads"),'thumbs')
		if not os.path.exists(self.thumbs_folder):
			os.makedirs(self.thumbs_folder)
		
	#~~ SettingsPlugin API

	def get_settings_defaults(self):
		return {
			"some_feature": None,
			"setting_list": {},
			"int_value": 24 * 60,
		}

	def on_settings_load(self):
		data = dict(octoprint.plugin.SettingsPlugin.on_settings_load(self))
		return data

	def on_settings_save(self, data):
		defaults = dict(
			param1="foo",
			param2="bar"
		)

	def get_settings_version(self):
		return 4

	#~~ TornadoRoute for serving thumbnails from uploads/thumbs/
	def route_hook(self, server_routes, *args, **kwargs):
		import os
		from octoprint.server.util.tornado import LargeResponseHandler, path_validation_factory
		thumbs_path = os.path.join(self._settings.global_get_basefolder("uploads"),'thumbs')

		return [
			(r"/thumbs/(.*)", LargeResponseHandler, dict(path=thumbs_path, as_attachment=False, path_validation=path_validation_factory(lambda path: not os.path.basename(path).startswith("."), status_code=404))),
			#(r"forward/(.*)", UrlForwardHandler, dict(url=self._settings.global_get(["webcam", "snapshot"]), as_attachment=True))
		]
		
	#~~ BluePrint API
	@octoprint.plugin.BlueprintPlugin.route("/thumb", methods=["POST"])
	def store_thumbnail(self):
		try:
			data = dict()
			
			print 'request.method', flask.request.method
			print 'request.args', flask.request.args
			print 'request.form', flask.request.form
			print 'request.files', flask.request.files
			print 'request.values', flask.request.values
			if 'file.path' in flask.request.form and 'file.name' in flask.request.form:
				tmp = flask.request.form['file.path']
				filename = flask.request.form['file.name']
				size = flask.request.form['file.size']
				
				# Check if the file is one of the allowed types/extensions
				if file and size > 0 and ('.' in filename and filename.rsplit('.', 1)[1] in ['jpg','png']):

					# Make the filename safe, remove unsupported chars
					filename = secure_filename(filename)

					# Move the file form the temporal folder to
					# the upload folder we setup
					import os
					import shutil
					dest = os.path.join(self.thumbs_folder, filename)
					shutil.move(tmp, dest)
					data['result'] = 'success'
					data['thumb_filename'] = filename
					data['thumb_url'] = '/plugin/bocusini_doodler/thumbs/'+filename
					return flask.jsonify(data)
					# Redirect the user to the uploaded_file route, which
					# will basicaly show on the browser the uploaded file
					#return redirect(url_for('uploaded_file', filename=filename))

				return flask.make_response(flask.jsonify(data), 201)
		except Exception as e:
			print(e.message)
			return flask.make_response("Storing thumbnail went wrong: %s" % e.message, 500)


	#~~ Asset API

	def get_assets(self):
		return dict(
			css=["css/bocusini_doodler.css","css/bocusini_styles.css", "css/bg_slideshow.css"],
			js=["js/doodle3d-api.js","js/print_settings.js", "js/bocusini_doodler.js","js/bocusini_client.js"],
			less=["less/bocusini_doodler.less"]
		)

	##~~ TemplatePlugin API

	def get_template_configs(self):
		from flask.ext.babel import gettext
		return [
			dict(type="generic", name=gettext("Bocusini Doodler")),
			dict(type="navbar", name=gettext("Bocusini Doodler"))
		]



__plugin_name__ = "Bocusini Doodler"
__plugin_author__ = "Print2Taste"
__plugin_url__ = "https://github.com/print2taste/... TBD"
__plugin_description__ = "Doodling UI for Bocusini foodprinter"
__plugin_license__ = "AGPLv3"
def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = BocusiniDoodlerPlugin()

	global __plugin_helpers__
	__plugin_helpers__ = dict(
		
	)
	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.server.http.routes": __plugin_implementation__.route_hook
	}

    

