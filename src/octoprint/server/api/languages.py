__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import logging
import os
import zipfile
from collections import defaultdict

from flask import abort, jsonify, request
from flask_babel import Locale

from octoprint.access.permissions import Permissions
from octoprint.plugin import plugin_manager
from octoprint.server.api import api
from octoprint.server.util.flask import no_firstrun_access
from octoprint.settings import settings
from octoprint.util import yaml


@api.route("/languages", methods=["GET"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def getInstalledLanguagePacks():
    translation_folder = settings().getBaseFolder("translations", check_writable=False)
    if not os.path.exists(translation_folder):
        return jsonify(language_packs={"_core": []})

    core_packs = []
    plugin_packs = defaultdict(
        lambda: {"identifier": None, "display": None, "languages": []}
    )
    for entry in os.scandir(translation_folder):
        if not entry.is_dir():
            continue

        def load_meta(path, locale):
            meta = {}

            meta_path = os.path.join(path, "meta.yaml")
            if os.path.isfile(meta_path):
                try:
                    meta = yaml.load_from_file(path=meta_path)
                except Exception:
                    logging.getLogger(__name__).exception("Could not load %s", meta_path)
                    pass
                else:
                    import datetime

                    if "last_update" in meta and isinstance(
                        meta["last_update"], datetime.datetime
                    ):
                        meta["last_update"] = (
                            meta["last_update"] - datetime.datetime(1970, 1, 1)
                        ).total_seconds()

            loc = Locale.parse(locale)
            meta["locale"] = str(loc)
            meta["locale_display"] = loc.display_name
            meta["locale_english"] = loc.english_name
            return meta

        if entry.name == "_plugins":
            for plugin_entry in os.scandir(entry.path):
                if not plugin_entry.is_dir():
                    continue

                if plugin_entry.name not in plugin_manager().plugins:
                    continue

                plugin_info = plugin_manager().plugins[plugin_entry.name]

                plugin_packs[plugin_entry.name]["identifier"] = plugin_entry.name
                plugin_packs[plugin_entry.name]["display"] = plugin_info.name

                for language_entry in os.scandir(plugin_entry.path):
                    try:
                        plugin_packs[plugin_entry.name]["languages"].append(
                            load_meta(language_entry.path, language_entry.name)
                        )
                    except Exception:
                        logging.getLogger(__name__).exception(
                            "Error while parsing metadata for language pack {} from {} for plugin {}".format(
                                language_entry.name,
                                language_entry.path,
                                plugin_entry.name,
                            )
                        )
                        continue
        else:
            try:
                core_packs.append(load_meta(entry.path, entry.name))
            except ValueError:
                logging.getLogger(__name__).exception(
                    "Core language pack {} doesn't appear to actually be one".format(
                        entry.name
                    )
                )
            except Exception:
                logging.getLogger(__name__).exception(
                    "Error while parsing metadata for core language pack {} from {}".format(
                        entry.name, entry.path
                    )
                )

    result = {
        "_core": {"identifier": "_core", "display": "Core", "languages": core_packs}
    }
    result.update(plugin_packs)
    return jsonify(language_packs=result)


@api.route("/languages", methods=["POST"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def uploadLanguagePack():
    input_name = "file"
    input_upload_path = (
        input_name + "." + settings().get(["server", "uploads", "pathSuffix"])
    )
    input_upload_name = (
        input_name + "." + settings().get(["server", "uploads", "nameSuffix"])
    )
    if input_upload_path not in request.values or input_upload_name not in request.values:
        abort(400, description="No file included")

    upload_name = request.values[input_upload_name]
    upload_path = request.values[input_upload_path]

    exts = list(
        filter(
            lambda x: upload_name.lower().endswith(x), (".zip", ".tar.gz", ".tgz", ".tar")
        )
    )
    if not len(exts):
        abort(
            400,
            description="File doesn't have a valid extension for a language pack archive",
        )

    target_path = settings().getBaseFolder("translations")

    if not zipfile.is_zipfile(upload_path):
        abort(400, description="No zip file included")

    if not _validate_and_install_language_pack(upload_path, target_path):
        abort(400, description="Invalid language pack archive")

    return getInstalledLanguagePacks()


@api.route("/languages/<string:locale>/<string:pack>", methods=["DELETE"])
@no_firstrun_access
@Permissions.SETTINGS.require(403)
def deleteInstalledLanguagePack(locale, pack):
    if pack == "_core":
        target_path = os.path.join(settings().getBaseFolder("translations"), locale)
    else:
        target_path = os.path.join(
            settings().getBaseFolder("translations"), "_plugins", pack, locale
        )

    if os.path.isdir(target_path):
        import shutil

        shutil.rmtree(target_path)

    return getInstalledLanguagePacks()


def _validate_and_install_language_pack(path, target):
    import tempfile

    if not zipfile.is_zipfile(path):
        return False

    something_installed = False
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(path, mode="r") as zip:
            # protect against path traversal
            if any(
                map(
                    lambda x: not os.path.abspath(os.path.join(temp_dir, x)).startswith(
                        temp_dir + os.path.sep
                    ),
                    zip.namelist(),
                )
            ):
                return False
            zip.extractall(temp_dir)

        something_installed = (
            _validate_and_install_translations(temp_dir, target) or something_installed
        )
        if os.path.exists(os.path.join(temp_dir, "_plugins")):
            something_installed = (
                _validate_and_install_plugin_language_pack(
                    os.path.join(temp_dir, "_plugins"), os.path.join(target, "_plugins")
                )
                or something_installed
            )

    return something_installed


def _validate_and_install_plugin_language_pack(path, target):
    something_installed = False

    for entry in os.scandir(path):
        if not entry.is_dir():
            continue

        something_installed = (
            _validate_and_install_translations(
                entry.path, os.path.join(target, entry.name)
            )
            or something_installed
        )

    return something_installed


def _validate_and_install_translations(path, target):
    import shutil

    from babel.core import Locale

    something_installed = False

    for entry in os.scandir(path):
        if not entry.is_dir():
            continue

        try:
            loc = Locale.parse(entry.name)
        except Exception:
            continue

        if not os.path.isfile(os.path.join(entry.path, "meta.yaml")):
            continue

        if not os.path.isdir(os.path.join(entry.path, "LC_MESSAGES")):
            continue

        if not os.path.isfile(os.path.join(entry.path, "LC_MESSAGES", "messages.mo")):
            continue

        # looks like a valid translation folder incl. metadata, let's move it
        if not os.path.exists(target):
            os.makedirs(target)
        shutil.move(entry.path, os.path.join(target, str(loc)))
        something_installed = True

    return something_installed


class InvalidLanguagePack(Exception):
    pass
