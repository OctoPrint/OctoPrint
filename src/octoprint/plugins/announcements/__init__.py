# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2016 The OctoPrint Project - Released under terms of the AGPLv3 License"


import octoprint.plugin

import calendar
import codecs
import os
import re
import time
import threading

import feedparser
import flask

from collections import OrderedDict

from octoprint.server import admin_permission
from octoprint.server.util.flask import restricted_access, with_revalidation_checking, check_etag
from octoprint.util import utmify
from flask.ext.babel import gettext
from octoprint import __version__ as OCTOPRINT_VERSION

class AnnouncementPlugin(octoprint.plugin.AssetPlugin,
                         octoprint.plugin.SettingsPlugin,
                         octoprint.plugin.BlueprintPlugin,
                         octoprint.plugin.StartupPlugin,
                         octoprint.plugin.TemplatePlugin,
                         octoprint.plugin.EventHandlerPlugin):

	# noinspection PyMissingConstructor
	def __init__(self):
		self._cached_channel_configs = None
		self._cached_channel_configs_mutex = threading.RLock()

		from slugify import Slugify
		self._slugify = Slugify()
		self._slugify.safe_chars = "-_."

	# StartupPlugin

	def on_after_startup(self):
		# decouple channel fetching from server startup
		def fetch_data():
			self._fetch_all_channels()

		thread = threading.Thread(target=fetch_data)
		thread.daemon = True
		thread.start()

	# SettingsPlugin

	def get_settings_defaults(self):
		settings = dict(channels=dict(_important=dict(name="Important Announcements",
		                                              description="Important announcements about OctoPrint.",
		                                              priority=1,
		                                              type="rss",
		                                              url="https://octoprint.org/feeds/important.xml"),
		                              _releases=dict(name="Release Announcements",
		                                             description="Announcements of new releases and release candidates of OctoPrint.",
		                                             priority=2,
		                                             type="rss",
		                                             url="https://octoprint.org/feeds/releases.xml"),
		                              _blog=dict(name="On the OctoBlog",
		                                         description="Development news, community spotlights, OctoPrint On Air episodes and more from the official OctoBlog.",
		                                         priority=2,
		                                         type="rss",
		                                         url="https://octoprint.org/feeds/octoblog.xml"),
		                              _plugins=dict(name="New Plugins in the Repository",
		                                            description="Announcements of new plugins released on the official Plugin Repository.",
		                                            priority=2,
		                                            type="rss",
		                                            url="https://plugins.octoprint.org/feed.xml"),
		                              _octopi=dict(name="OctoPi News",
		                                           description="News around OctoPi, the Raspberry Pi image including OctoPrint.",
		                                           priority=2,
		                                           type="rss",
		                                           url="https://octoprint.org/feeds/octopi.xml")),
		                enabled_channels=[],
		                forced_channels=["_important"],
		                channel_order=["_important", "_releases", "_blog", "_plugins", "_octopi"],
		                ttl=6*60,
		                display_limit=3,
		                summary_limit=300)
		settings["enabled_channels"] = settings["channels"].keys()
		return settings

	def get_settings_version(self):
		return 1

	def on_settings_migrate(self, target, current):
		if current is None:
			# first version had different default feeds and only _important enabled by default
			channels = self._settings.get(["channels"])
			if "_news" in channels:
				del channels["_news"]
			if "_spotlight" in channels:
				del channels["_spotlight"]
			self._settings.set(["channels"], channels)

			enabled = self._settings.get(["enabled_channels"])
			add_blog = False
			if "_news" in enabled:
				add_blog = True
				enabled.remove("_news")
			if "_spotlight" in enabled:
				add_blog = True
				enabled.remove("_spotlight")
			if add_blog and not "_blog" in enabled:
				enabled.append("_blog")
			self._settings.set(["enabled_channels"], enabled)

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
		from octoprint.settings import valid_boolean_trues

		result = []

		force = flask.request.values.get("force", "false") in valid_boolean_trues

		enabled = self._settings.get(["enabled_channels"])
		forced = self._settings.get(["forced_channels"])

		channel_configs = self._get_channel_configs(force=force)

		def view():
			channel_data = self._fetch_all_channels(force=force)

			for key, data in channel_configs.items():
				read_until = channel_configs[key].get("read_until", None)
				entries = sorted(self._to_internal_feed(channel_data.get(key, []), read_until=read_until), key=lambda e: e["published"], reverse=True)
				unread = len(filter(lambda e: not e["read"], entries))

				if read_until is None and entries:
					last = entries[0]["published"]
					self._mark_read_until(key, last)

				result.append(dict(key=key,
				                   channel=data["name"],
				                   url=data["url"],
				                   description=data.get("description", ""),
				                   priority=data.get("priority", 2),
				                   enabled=key in enabled or key in forced,
				                   forced=key in forced,
				                   data=entries,
				                   unread=unread))

			return flask.jsonify(channels=result)

		def etag():
			import hashlib
			hash = hashlib.sha1()
			hash.update(repr(sorted(enabled)))
			hash.update(repr(sorted(forced)))
			hash.update(OCTOPRINT_VERSION)

			for channel in sorted(channel_configs.keys()):
				hash.update(repr(channel_configs[channel]))
				channel_data = self._get_channel_data_from_cache(channel, channel_configs[channel])
				hash.update(repr(channel_data))

			return hash.hexdigest()

		# noinspection PyShadowingNames
		def condition(lm, etag):
			return check_etag(etag)

		return with_revalidation_checking(etag_factory=lambda *args, **kwargs: etag(),
		                                  condition=lambda lm, etag: condition(lm, etag),
		                                  unless=lambda: force)(view)()

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
			until = data["until"]
			self._mark_read_until(channel, until)

		elif command == "toggle":
			self._toggle(channel)

		return NO_CONTENT

	##~~ EventHandlerPlugin

	def on_event(self, event, payload):
		from octoprint.events import Events
		if event != Events.CONNECTIVITY_CHANGED or not payload or not payload.get("new", False):
			return
		self._fetch_all_channels_async()

	# Internal Tools

	def _mark_read_until(self, channel, until):
		"""Set read_until timestamp of a channel."""

		current_read_until = None
		channel_data = self._settings.get(["channels", channel], merged=True)
		if channel_data:
			current_read_until = channel_data.get("read_until", None)

		defaults = dict(plugins=dict(announcements=dict(channels=dict())))
		defaults["plugins"]["announcements"]["channels"][channel] = dict(read_until=current_read_until)

		with self._cached_channel_configs_mutex:
			self._settings.set(["channels", channel, "read_until"], until, defaults=defaults)
			self._settings.save()
			self._cached_channel_configs = None

	def _toggle(self, channel):
		"""Toggle enable/disabled state of a channel."""

		enabled_channels = list(self._settings.get(["enabled_channels"]))

		if channel in enabled_channels:
			enabled_channels.remove(channel)
		else:
			enabled_channels.append(channel)

		self._settings.set(["enabled_channels"], enabled_channels)
		self._settings.save()

	def _get_channel_configs(self, force=False):
		"""Retrieve all channel configs with sanitized keys."""

		with self._cached_channel_configs_mutex:
			if self._cached_channel_configs is None or force:
				configs = self._settings.get(["channels"], merged=True)
				order = self._settings.get(["channel_order"])
				all_keys = order + [key for key in sorted(configs.keys()) if not key in order]

				result = OrderedDict()
				for key in all_keys:
					config = configs.get(key)
					if config is None or "url" not in config or "name" not in config:
						# strip invalid entries
						continue
					result[self._slugify(key)] = config
				self._cached_channel_configs = result
		return self._cached_channel_configs

	def _get_channel_config(self, key, force=False):
		"""Retrieve specific channel config for channel."""

		safe_key = self._slugify(key)
		return self._get_channel_configs(force=force).get(safe_key)

	def _fetch_all_channels_async(self, force=False):
		thread = threading.Thread(target=self._fetch_all_channels, kwargs=dict(force=force))
		thread.daemon = True
		thread.start()

	def _fetch_all_channels(self, force=False):
		"""Fetch all channel feeds from cache or network."""

		channels = self._get_channel_configs(force=force)
		enabled = self._settings.get(["enabled_channels"])
		forced = self._settings.get(["forced_channels"])

		all_channels = dict()
		for key, config in channels.items():
			if not key in enabled and not key in forced:
				continue

			if not "url" in config:
				continue

			data = self._get_channel_data(key, config, force=force)
			if data is not None:
				all_channels[key] = data

		return all_channels

	def _get_channel_data(self, key, config, force=False):
		"""Fetch individual channel feed from cache/network."""

		data = None

		if not force:
			# we may use the cache, see if we have something in there
			data = self._get_channel_data_from_cache(key, config)

		if data is None:
			# cache not allowed or empty, fetch from network
			if self._connectivity_checker.online:
				data = self._get_channel_data_from_network(key, config)
			else:
				self._logger.info("Looks like we are offline, can't fetch announcements for channel {} from network".format(key))

		return data

	def _get_channel_data_from_cache(self, key, config):
		"""Fetch channel feed from cache."""

		channel_path = self._get_channel_cache_path(key)

		if os.path.exists(channel_path):
			if "ttl" in config and isinstance(config["ttl"], int):
				ttl = config["ttl"]
			else:
				ttl = self._settings.get_int(["ttl"])

			ttl *= 60
			now = time.time()
			if os.stat(channel_path).st_mtime + ttl > now:
				d = feedparser.parse(channel_path)
				self._logger.debug(u"Loaded channel {} from cache at {}".format(key, channel_path))
				return d

		return None

	def _get_channel_data_from_network(self, key, config):
		"""Fetch channel feed from network."""

		import requests

		url = config["url"]
		try:
			start = time.time()
			r = requests.get(url, timeout=30)
			r.raise_for_status()
			self._logger.info(u"Loaded channel {} from {} in {:.2}s".format(key, config["url"], time.time() - start))
		except Exception as e:
			self._logger.exception(
				u"Could not fetch channel {} from {}: {}".format(key, config["url"], str(e)))
			return None

		response = r.text
		channel_path = self._get_channel_cache_path(key)
		with codecs.open(channel_path, mode="w", encoding="utf-8") as f:
			f.write(response)
		return feedparser.parse(response)

	def _to_internal_feed(self, feed, read_until=None):
		"""Convert feed to internal data structure."""

		result = []
		if "entries" in feed:
			for entry in feed["entries"]:
				internal_entry = self._to_internal_entry(entry, read_until=read_until)
				if internal_entry:
					result.append(internal_entry)
		return result

	def _to_internal_entry(self, entry, read_until=None):
		"""Convert feed entries to internal data structure."""

		published = calendar.timegm(entry["published_parsed"])

		read = True
		if read_until is not None:
			read = published <= read_until

		return dict(title=entry["title"],
		            title_without_tags=_strip_tags(entry["title"]),
		            summary=_lazy_images(entry["summary"]),
		            summary_without_images=_strip_images(entry["summary"]),
		            published=published,
		            link=utmify(entry["link"], source="octoprint", medium="announcements", content=OCTOPRINT_VERSION),
		            read=read)

	def _get_channel_cache_path(self, key):
		"""Retrieve cache path for channel key."""

		safe_key = self._slugify(key)
		return os.path.join(self.get_plugin_data_folder(), "{}.cache".format(safe_key))


_image_tag_re = re.compile(r'<img.*?/?>')
def _strip_images(text):
	"""
	>>> _strip_images(u"<a href='test.html'>I'm a link</a> and this is an image: <img src='foo.jpg' alt='foo'>")
	u"<a href='test.html'>I'm a link</a> and this is an image: "
	>>> _strip_images(u"One <img src=\\"one.jpg\\"> and two <img src='two.jpg' > and three <img src=three.jpg> and four <img src=\\"four.png\\" alt=\\"four\\">")
	u'One  and two  and three  and four '
	>>> _strip_images(u"No images here")
	u'No images here'
	"""
	return _image_tag_re.sub('', text)

def _replace_images(text, callback):
	"""
	>>> callback = lambda img: "foobar"
	>>> _replace_images(u"<a href='test.html'>I'm a link</a> and this is an image: <img src='foo.jpg' alt='foo'>", callback)
	u"<a href='test.html'>I'm a link</a> and this is an image: foobar"
	>>> _replace_images(u"One <img src=\\"one.jpg\\"> and two <img src='two.jpg' > and three <img src=three.jpg> and four <img src=\\"four.png\\" alt=\\"four\\">", callback)
	u'One foobar and two foobar and three foobar and four foobar'
	"""
	result = text
	for match in _image_tag_re.finditer(text):
		tag = match.group(0)
		replaced = callback(tag)
		result = result.replace(tag, replaced)
	return result

_image_src_re = re.compile(r'src=(?P<quote>[\'"]*)(?P<src>.*?)(?P=quote)(?=\s+|>)')
def _lazy_images(text, placeholder=None):
	"""
	>>> _lazy_images(u"<a href='test.html'>I'm a link</a> and this is an image: <img src='foo.jpg' alt='foo'>")
	u'<a href=\\'test.html\\'>I\\'m a link</a> and this is an image: <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" data-src=\\'foo.jpg\\' alt=\\'foo\\'>'
	>>> _lazy_images(u"<a href='test.html'>I'm a link</a> and this is an image: <img src='foo.jpg' alt='foo'>", placeholder="ph.png")
	u'<a href=\\'test.html\\'>I\\'m a link</a> and this is an image: <img src="ph.png" data-src=\\'foo.jpg\\' alt=\\'foo\\'>'
	>>> _lazy_images(u"One <img src=\\"one.jpg\\"> and two <img src='two.jpg' > and three <img src=three.jpg> and four <img src=\\"four.png\\" alt=\\"four\\">", placeholder="ph.png")
	u'One <img src="ph.png" data-src="one.jpg"> and two <img src="ph.png" data-src=\\'two.jpg\\' > and three <img src="ph.png" data-src=three.jpg> and four <img src="ph.png" data-src="four.png" alt="four">'
	>>> _lazy_images(u"No images here")
	u'No images here'
	"""
	if placeholder is None:
		# 1px transparent gif
		placeholder = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

	def callback(img_tag):
		match = _image_src_re.search(img_tag)
		if match is not None:
			src = match.group("src")
			quote = match.group("quote")
			quoted_src = quote + src + quote
			img_tag = img_tag.replace(match.group(0), 'src="{}" data-src={}'.format(placeholder, quoted_src))
		return img_tag

	return _replace_images(text, callback)

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
__plugin_author__ = "Gina Häußge"
__plugin_description__ = "Announcements all around OctoPrint"
__plugin_disabling_discouraged__ = gettext("Without this plugin you might miss important announcements "
                                           "regarding security or other critical issues concerning OctoPrint.")
__plugin_license__ = "AGPLv3"
__plugin_implementation__ = AnnouncementPlugin()
