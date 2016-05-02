# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin

import codecs
import datetime
import os
import re
import time
import threading

import feedparser
import flask

from octoprint.server import admin_permission
from octoprint.server.util.flask import restricted_access
from flask.ext.babel import gettext

class AnnouncementPlugin(octoprint.plugin.AssetPlugin,
                         octoprint.plugin.SettingsPlugin,
                         octoprint.plugin.BlueprintPlugin,
                         octoprint.plugin.StartupPlugin,
                         octoprint.plugin.TemplatePlugin):

	def __init__(self):
		self._cached_channels = dict()
		self._cached_channels_mutex = threading.RLock()

	# StartupPlugin

	def on_after_startup(self):
		self._fetch_all_channels()

	# SettingsPlugin

	def get_settings_defaults(self):
		return dict(channels=dict(_important=dict(name="Important OctoPrint Announcements",
		                                          priority=1,
		                                          type="rss",
		                                          url="http://octoprint.org/feeds/important.xml",
		                                          read_until=1449442800),
		                          _releases=dict(name="OctoPrint Release Announcements",
		                                         priority=2,
		                                         type="rss",
		                                         url="http://octoprint.org/feeds/releases.xml",
		                                         read_until=1458117576),
		                          _spotlight=dict(name="OctoPrint Community Spotlights",
		                                          priority=2,
		                                          type="rss",
		                                          url="http://octoprint.org/feeds/spotlight.xml",
		                                          read_until=1447950371),
		                          _octopi=dict(name="OctoPi Announcements",
		                                       priority=2,
		                                       type="rss",
		                                       url="http://octoprint.org/feeds/octopi.xml",
		                                       read_until=1462197000),
		                          _plugins=dict(name="New Plugins in the Repository",
		                                        priority=2,
		                                        type="rss",
		                                        url="http://plugins.octoprint.org/feed.xml",
		                                        read_until=1461625200)),
		            enabled_channels=[],
		            forced_channels=["_important"],
		            ttl=6*60,
		            display_limit=3,
		            summary_limit=300)

	# AssetPlugin

	def get_assets(self):
		return dict(js=["js/announcements.js"],
		            less=["less/announcements.less"],
		            css=["css/announcements.css"])

	# Template Plugin

	def get_template_configs(self):
		return [
			dict(type="settings", name=gettext("Announcements"), template="announcements_settings.jinja2", custom_bindings=True),
			dict(type="navbar", template="announcements_navbar.jinja2", styles=["display: none"], data_bind="visible: loginState.isAdmin")
		]

	# Blueprint Plugin

	@octoprint.plugin.BlueprintPlugin.route("/channels", methods=["GET"])
	@restricted_access
	@admin_permission.require(403)
	def get_channel_data(self):
		result = dict()

		channel_data = self._fetch_all_channels()

		channel_configs = self._get_channel_configs()
		enabled = self._settings.get(["enabled_channels"])
		forced = self._settings.get(["forced_channels"])
		for key, data in channel_configs.items():
			entries = self._to_internal_feed(channel_data.get(key, []), read_until=channel_configs[key].get("read_until", None))
			unread = len(filter(lambda e: not e["read"], entries))

			result[key] = dict(channel=data["name"],
			                   url=data["url"],
			                   priority=data["priority"],
			                   enabled=key in enabled or key in forced,
			                   forced=key in forced,
			                   data=entries,
			                   unread=unread)

		return flask.jsonify(result)

	@octoprint.plugin.BlueprintPlugin.route("/channels/<channel>", methods=["POST"])
	@restricted_access
	@admin_permission.require(403)
	def channel_command(self, channel):
		from octoprint.server.util.flask import get_json_command_from_request
		from octoprint.server import NO_CONTENT

		valid_commands = dict(read=["until"],
		                      toggle=[])

		command, data, response = get_json_command_from_request(flask.request, valid_commands=valid_commands)
		if response is not None:
			return response

		if command == "read":
			current_read_until = None
			channel_data = self._settings.get(["channels", channel], merged=True)
			if channel_data:
				current_read_until = channel_data.get("read_until", None)

			defaults = dict(plugins=dict(announcements=dict(channels=dict())))
			defaults["plugins"]["announcements"]["channels"][channel] = dict(read_until=current_read_until)

			until = data["until"]
			self._settings.set(["channels", channel, "read_until"], until, defaults=defaults)
			self._settings.save()

		elif command == "toggle":
			enabled_channels = list(self._settings.get(["enabled_channels"]))

			if channel in enabled_channels:
				enabled_channels.remove(channel)
			else:
				enabled_channels.append(channel)

			self._settings.set(["enabled_channels"], enabled_channels)
			self._settings.save()

		return NO_CONTENT

	# Internal Tools

	def _get_channel_configs(self):
		return self._settings.get(["channels"], merged=True)

	def _fetch_all_channels(self):
		with self._cached_channels_mutex:
			channels = self._get_channel_configs()
			enabled = self._settings.get(["enabled_channels"])
			forced = self._settings.get(["forced_channels"])

			all_channels = dict()
			for key, config in channels.items():
				if not key in enabled and not key in forced:
					continue

				data = self._get_channel_data(key, config)
				if data is not None:
					all_channels[key] = data

			self._cached_channels = all_channels

		return self._cached_channels

	def _get_channel_data(self, key, config):
		data = self._get_channel_data_from_cache(key, config)
		if data is None:
			data = self._get_channel_data_from_network(key, config)
		return data

	def _get_channel_data_from_cache(self, key, config):
		channel_path = os.path.join(self.get_plugin_data_folder(), "{}.cache".format(key))

		if os.path.exists(channel_path):
			if "ttl" in config and isinstance(config["ttl"], int):
				ttl = config["ttl"]
			else:
				ttl = self._settings.get_int(["ttl"])

			ttl *= 60
			now = time.time()
			if os.stat(channel_path).st_mtime + ttl > now:
				d = feedparser.parse(channel_path)
				self._logger.info("Loaded channel {} from cache".format(key))
				return d

		return None

	def _get_channel_data_from_network(self, key, config):
		import requests

		url = config["url"]
		try:
			r = requests.get(url)
			self._logger.info("Loaded channel {} from {}".format(key, config["url"]))
		except Exception as e:
			self._logger.exception(
				"Could not fetch channel {} from {}: {}".format(key, config["url"], str(e)))
			return None

		response = r.text
		channel_path = os.path.join(self.get_plugin_data_folder(), "{}.cache".format(key))
		with codecs.open(channel_path, mode="w", encoding="utf-8") as f:
			f.write(response)
		return feedparser.parse(response)

	def _to_internal_feed(self, feed, read_until=None):
		result = []
		if "entries" in feed:
			for entry in feed["entries"]:
				internal_entry = self._to_internal_entry(entry, read_until=read_until)
				if internal_entry:
					result.append(internal_entry)
		return result

	def _to_internal_entry(self, entry, read_until=None):
		published = time.mktime(entry["published_parsed"])

		read = False
		if read_until is not None:
			read = published <= read_until

		return dict(title=entry["title"],
		            title_without_tags=_strip_tags(entry["title"]),
		            summary=entry["summary"],
		            summary_without_images=_strip_images(entry["summary"]),
		            published=published,
		            link=entry["link"],
		            read=read)


_image_tag_re = re.compile(r'<img.*?/?>')
def _strip_images(text):
	return _image_tag_re.sub('', text)


def _strip_tags(text):
	"""
	>>> _strip_tags(u"<a href='test.html'>Hello world</a>&lt;img src='foo.jpg'&gt;")
	u"Hello world&lt;img src='foo.jpg'&gt;"
	>>> _strip_tags(u"&#62; &#x3E; Foo")
	u'&#62; &#x3E; Foo'
	"""

	from HTMLParser import HTMLParser

	class TagStripper(HTMLParser):

		def __init__(self):
			HTMLParser.__init__(self)
			self._fed = []

		def handle_data(self, data):
			self._fed.append(data)

		def handle_entityref(self, ref):
			self._fed.append("&{};".format(ref))

		def handle_charref(self, ref):
			self._fed.append("&#{};".format(ref))

		def get_data(self):
			return "".join(self._fed)

	tag_stripper = TagStripper()
	tag_stripper.feed(text)
	return tag_stripper.get_data()


__plugin_name__ = "Announcement Plugin"
__plugin_implementation__ = AnnouncementPlugin()
