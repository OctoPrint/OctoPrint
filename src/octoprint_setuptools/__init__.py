# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

# NO unicode_literals because Py2 setuptool can't cope with them

__author__ = u"Gina Häußge <osd@foosel.net>"
__license__ = u"GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = u"Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import glob
import os
import shutil
from distutils.command.clean import clean as _clean

from setuptools import Command


def package_data_dirs(source, sub_folders):
    dirs = []

    for d in sub_folders:
        folder = os.path.join(source, d)
        if not os.path.exists(folder):
            continue

        for dirname, _, files in os.walk(folder):
            dirname = os.path.relpath(dirname, source)
            for f in files:
                dirs.append(os.path.join(dirname, f))

    return dirs


def recursively_handle_files(
    directory, file_matcher, folder_matcher=None, folder_handler=None, file_handler=None
):
    applied_handler = False

    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)

        if file_handler is not None and file_matcher(filename):
            file_handler(path)
            applied_handler = True

        elif os.path.isdir(path) and (
            folder_matcher is None or folder_matcher(directory, filename, path)
        ):
            sub_applied_handler = recursively_handle_files(
                path,
                file_matcher,
                folder_handler=folder_handler,
                file_handler=file_handler,
            )
            if sub_applied_handler:
                applied_handler = True

            if folder_handler is not None:
                folder_handler(path, sub_applied_handler)

    return applied_handler


def has_requirement(requirement, requirements):
    if requirement is None or requirements is None:
        return False

    # from past.builtins import basestring

    # assert isinstance(requirement, basestring)
    # assert isinstance(requirements, (list, tuple))
    # assert all(list(map(lambda x: x is not None and isinstance(x, basestring), requirements)))

    requirement = requirement.lower()
    requirements = [r.lower() for r in requirements]
    compat = [
        requirement.lower() + c for c in ("<", "<=", "!=", "==", ">=", ">", "~=", "===")
    ]

    return requirement in requirements or any(
        any(r.startswith(c) for c in compat) for r in requirements
    )


class CleanCommand(_clean):
    user_options = _clean.user_options + [
        ("orig", None, "behave like original clean command"),
        ("noeggs", None, "don't clean up eggs"),
        ("nopyc", None, "don't clean up pyc files"),
    ]
    boolean_options = _clean.boolean_options + ["orig", "noeggs", "nopyc"]

    source_folder = "src"
    eggs = None

    @classmethod
    def for_options(cls, source_folder="src", eggs=None):
        if eggs is None:
            eggs = []
        return type(cls)(
            cls.__name__, (cls,), {"source_folder": source_folder, "eggs": eggs}
        )

    def initialize_options(self):
        _clean.initialize_options(self)

        self.orig = None
        self.noeggs = None
        self.nopyc = None

    def finalize_options(self):
        _clean.finalize_options(self)

        if not self.orig:
            self.all = True

    def run(self):
        _clean.run(self)
        if self.orig:
            return

        # eggs
        if not self.noeggs:
            for egg in self.eggs:
                globbed_eggs = glob.glob(egg)
                for globbed_egg in globbed_eggs:
                    print("deleting '%s' egg" % globbed_egg)
                    if not self.dry_run:
                        shutil.rmtree(globbed_egg)

        # pyc files
        if not self.nopyc:

            def delete_folder_if_empty(path, applied_handler):
                if not applied_handler:
                    return
                if len(os.listdir(path)) == 0:
                    if not self.dry_run:
                        shutil.rmtree(path)
                    print(
                        "removed %s since it was empty" % path[len(self.source_folder) :]
                    )

            def delete_file(path):
                print("removing '%s'" % path[len(self.source_folder) :])
                if not self.dry_run:
                    os.remove(path)

            import fnmatch

            print("recursively removing *.pyc from '%s'" % self.source_folder)
            recursively_handle_files(
                os.path.abspath(self.source_folder),
                lambda name: fnmatch.fnmatch(name.lower(), "*.pyc"),
                folder_matcher=lambda dir, name, path: name != ".git",
                folder_handler=delete_folder_if_empty,
                file_handler=delete_file,
            )


class NewTranslation(Command):
    description = "create a new translation"
    user_options = [
        ("locale=", "l", "locale for the new translation"),
    ]
    boolean_options = []

    pot_file = None
    output_dir = None

    @classmethod
    def for_options(cls, pot_file=None, output_dir=None):
        if pot_file is None:
            raise ValueError("pot_file must not be None")
        if output_dir is None:
            raise ValueError("output_dir must not be None")

        return type(cls)(
            cls.__name__, (cls,), {"pot_file": pot_file, "output_dir": output_dir}
        )

    def __init__(self, dist, **kw):
        from babel.messages import frontend as babel

        self.babel_init_messages = babel.init_catalog(dist)
        Command.__init__(self, dist, **kw)

    def initialize_options(self):
        self.locale = None
        self.babel_init_messages.initialize_options()

    def finalize_options(self):
        self.babel_init_messages.locale = self.locale
        self.babel_init_messages.input_file = self.__class__.pot_file
        self.babel_init_messages.output_dir = self.__class__.output_dir
        self.babel_init_messages.finalize_options()

    def run(self):
        self.babel_init_messages.run()


class ExtractTranslation(Command):
    description = "extract translations"
    user_options = []
    boolean_options = []

    mail_address = "i18n@octoprint.org"
    copyright_holder = "The OctoPrint Project"
    mapping_file = None
    pot_file = None
    input_dirs = None

    @classmethod
    def for_options(
        cls,
        mail_address="i18n@octoprint.org",
        copyright_holder="The OctoPrint Project",
        mapping_file=None,
        pot_file=None,
        input_dirs=None,
    ):
        if mapping_file is None:
            raise ValueError("mapping_file must not be None")
        if pot_file is None:
            raise ValueError("pot_file must not be None")
        if input_dirs is None:
            raise ValueError("input_dirs must not be None")

        return type(cls)(
            cls.__name__,
            (cls,),
            {
                "mapping_file": mapping_file,
                "pot_file": pot_file,
                "input_dirs": input_dirs,
                "mail_address": mail_address,
                "copyright_holder": copyright_holder,
            },
        )

    def __init__(self, dist, **kw):
        from babel.messages import frontend as babel

        self.babel_extract_messages = babel.extract_messages(dist)
        Command.__init__(self, dist, **kw)

    def initialize_options(self):
        self.babel_extract_messages.initialize_options()

    def finalize_options(self):
        self.babel_extract_messages.mapping_file = self.__class__.mapping_file
        self.babel_extract_messages.output_file = self.__class__.pot_file
        self.babel_extract_messages.input_dirs = self.__class__.input_dirs
        self.babel_extract_messages.msgid_bugs_address = self.__class__.mail_address
        self.babel_extract_messages.copyright_holder = self.__class__.copyright_holder
        self.babel_extract_messages.finalize_options()

    def run(self):
        self.babel_extract_messages.run()


class RefreshTranslation(Command):
    description = "refresh translations"
    user_options = [
        ("locale=", "l", "locale for the translation to refresh"),
    ]
    boolean_options = []

    mail_address = "i18n@octoprint.org"
    copyright_holder = "The OctoPrint Project"
    mapping_file = None
    pot_file = None
    input_dirs = None
    output_dir = None

    @classmethod
    def for_options(
        cls,
        mail_address="i18n@octoprint.org",
        copyright_holder="The OctoPrint Project",
        mapping_file=None,
        pot_file=None,
        input_dirs=None,
        output_dir=None,
    ):
        if mapping_file is None:
            raise ValueError("mapping_file must not be None")
        if pot_file is None:
            raise ValueError("pot_file must not be None")
        if input_dirs is None:
            raise ValueError("input_dirs must not be None")
        if output_dir is None:
            raise ValueError("output_dir must not be None")

        return type(cls)(
            cls.__name__,
            (cls,),
            {
                "mapping_file": mapping_file,
                "pot_file": pot_file,
                "input_dirs": input_dirs,
                "mail_address": mail_address,
                "copyright_holder": copyright_holder,
                "output_dir": output_dir,
            },
        )

    def __init__(self, dist, **kw):
        from babel.messages import frontend as babel

        self.babel_extract_messages = babel.extract_messages(dist)
        self.babel_update_messages = babel.update_catalog(dist)
        Command.__init__(self, dist, **kw)

    def initialize_options(self):
        self.locale = None
        self.babel_extract_messages.initialize_options()
        self.babel_update_messages.initialize_options()

    def finalize_options(self):
        self.babel_extract_messages.mapping_file = self.__class__.mapping_file
        self.babel_extract_messages.output_file = self.__class__.pot_file
        self.babel_extract_messages.input_dirs = self.__class__.input_dirs
        self.babel_extract_messages.msgid_bugs_address = self.__class__.mail_address
        self.babel_extract_messages.copyright_holder = self.__class__.copyright_holder
        self.babel_extract_messages.finalize_options()

        self.babel_update_messages.input_file = self.__class__.pot_file
        self.babel_update_messages.output_dir = self.__class__.output_dir
        self.babel_update_messages.locale = self.locale
        self.babel_update_messages.finalize_options()

    def run(self):
        self.babel_extract_messages.run()
        self.babel_update_messages.run()


class CompileTranslation(Command):
    description = "compile translations"
    user_options = []
    boolean_options = []

    output_dir = None

    @classmethod
    def for_options(cls, output_dir=None):
        if output_dir is None:
            raise ValueError("output_dir must not be None")

        return type(cls)(cls.__name__, (cls,), {"output_dir": output_dir})

    def __init__(self, dist, **kw):
        from babel.messages import frontend as babel

        self.babel_compile_messages = babel.compile_catalog(dist)
        Command.__init__(self, dist, **kw)

    def initialize_options(self):
        self.babel_compile_messages.initialize_options()

    def finalize_options(self):
        self.babel_compile_messages.directory = self.__class__.output_dir
        self.babel_compile_messages.finalize_options()

    def run(self):
        self.babel_compile_messages.run()


class BundleTranslation(Command):
    description = "bundles translations"
    user_options = [("locale=", "l", "locale for the translation to bundle")]
    boolean_options = []

    source_dir = None
    target_dir = None

    @classmethod
    def for_options(cls, source_dir=None, target_dir=None):
        if source_dir is None:
            raise ValueError("source_dir must not be None")
        if target_dir is None:
            raise ValueError("target_dir must not be None")

        return type(cls)(
            cls.__name__, (cls,), {"source_dir": source_dir, "target_dir": target_dir}
        )

    def initialize_options(self):
        self.locale = None

    def finalize_options(self):
        pass

    def run(self):
        locale = self.locale
        source_path = os.path.join(self.__class__.source_dir, locale)
        target_path = os.path.join(self.__class__.target_dir, locale)

        if not os.path.exists(source_path):
            raise RuntimeError("source path " + source_path + " does not exist")

        if os.path.exists(target_path):
            if not os.path.isdir(target_path):
                raise RuntimeError(
                    "target path " + target_path + " exists and is not a directory"
                )
            shutil.rmtree(target_path)

        print(
            "Copying translations for locale {locale} from {source_path} to {target_path}...".format(
                **locals()
            )
        )
        shutil.copytree(source_path, target_path)


class PackTranslation(Command):
    description = "creates language packs for translations"
    user_options = [
        ("locale=", "l", "locale for the translation to pack"),
        ("author=", "a", "author of the translation"),
        ("target=", "t", "target folder for the pack"),
    ]
    boolean_options = []

    source_dir = None
    pack_name_prefix = None
    pack_path_prefix = None

    @classmethod
    def for_options(cls, source_dir=None, pack_name_prefix=None, pack_path_prefix=None):
        if source_dir is None:
            raise ValueError("source_dir must not be None")
        if pack_name_prefix is None:
            raise ValueError("pack_name_prefix must not be None")
        if pack_path_prefix is None:
            raise ValueError("pack_path_prefix must not be None")

        return type(cls)(
            cls.__name__,
            (cls,),
            {
                "source_dir": source_dir,
                "pack_name_prefix": pack_name_prefix,
                "pack_path_prefix": pack_path_prefix,
            },
        )

    def initialize_options(self):
        self.locale = None
        self.author = None
        self.target = None

    def finalize_options(self):
        if self.locale is None:
            raise ValueError("locale must be provided")

    def run(self):
        locale = self.locale
        locale_dir = os.path.join(self.__class__.source_dir, locale)

        if not os.path.isdir(locale_dir):
            raise RuntimeError("translation does not exist, please create it first")

        import datetime

        now = datetime.datetime.utcnow().replace(microsecond=0)

        if self.target is None:
            self.target = self.__class__.source_dir

        zip_path = os.path.join(
            self.target,
            "{prefix}{locale}_{date}.zip".format(
                prefix=self.__class__.pack_name_prefix,
                locale=locale,
                date=now.strftime("%Y%m%d%H%M%S"),
            ),
        )
        print("Packing translation to {zip_path}".format(**locals()))

        def add_recursively(zip, path, prefix):
            if not os.path.isdir(path):
                return

            for entry in os.listdir(path):
                entry_path = os.path.join(path, entry)
                new_prefix = prefix + "/" + entry
                if os.path.isdir(entry_path):
                    add_recursively(zip, entry_path, new_prefix)
                elif os.path.isfile(entry_path):
                    print("Adding {entry_path} as {new_prefix}".format(**locals()))
                    zip.write(entry_path, new_prefix)

        meta_str = "last_update: {date}\n".format(date=now.isoformat())
        if self.author:
            meta_str += "author: {author}\n".format(author=self.author)

        zip_locale_root = self.__class__.pack_path_prefix + locale

        import zipfile

        with zipfile.ZipFile(zip_path, "w") as zip:
            add_recursively(zip, locale_dir, zip_locale_root)

            print("Adding meta.yaml as {zip_locale_root}/meta.yaml".format(**locals()))
            zip.writestr(zip_locale_root + "/meta.yaml", meta_str)


def get_babel_commandclasses(
    pot_file=None,
    mapping_file="babel.cfg",
    input_dirs=".",
    output_dir=None,
    pack_name_prefix=None,
    pack_path_prefix=None,
    bundled_dir=None,
    mail_address="i18n@octoprint.org",
    copyright_holder="The OctoPrint Project",
):
    result = {
        "babel_new": NewTranslation.for_options(pot_file=pot_file, output_dir=output_dir),
        "babel_extract": ExtractTranslation.for_options(
            mapping_file=mapping_file,
            pot_file=pot_file,
            input_dirs=input_dirs,
            mail_address=mail_address,
            copyright_holder=copyright_holder,
        ),
        "babel_refresh": RefreshTranslation.for_options(
            mapping_file=mapping_file,
            pot_file=pot_file,
            input_dirs=input_dirs,
            output_dir=output_dir,
            mail_address=mail_address,
            copyright_holder=copyright_holder,
        ),
        "babel_compile": CompileTranslation.for_options(output_dir=output_dir),
        "babel_pack": PackTranslation.for_options(
            source_dir=output_dir,
            pack_name_prefix=pack_name_prefix,
            pack_path_prefix=pack_path_prefix,
        ),
    }

    if bundled_dir is not None:
        result["babel_bundle"] = BundleTranslation.for_options(
            source_dir=output_dir, target_dir=bundled_dir
        )

    return result


def create_plugin_setup_parameters(
    identifier="todo",
    name="TODO",
    version="0.1",
    description="TODO",
    author="TODO",
    mail="todo@example.com",
    url="TODO",
    license="AGPLv3",
    source_folder=".",
    additional_data=None,
    additional_packages=None,
    ignored_packages=None,
    requires=None,
    extra_requires=None,
    cmdclass=None,
    eggs=None,
    package=None,
    dependency_links=None,
):
    import pkg_resources

    if package is None:
        package = "octoprint_{identifier}".format(**locals())

    if additional_data is None:
        additional_data = list()

    if additional_packages is None:
        additional_packages = list()

    if ignored_packages is None:
        ignored_packages = list()

    if dependency_links is None:
        dependency_links = list()

    if requires is None:
        requires = ["OctoPrint"]
    if not isinstance(requires, list):
        raise ValueError("requires must be a list")
    if not has_requirement("OctoPrint", requires):
        requires = ["OctoPrint"] + list(requires)

    if extra_requires is None:
        extra_requires = {}
    if not isinstance(extra_requires, dict):
        raise ValueError("extra_requires must be a dict")

    if cmdclass is None:
        cmdclass = {}
    if not isinstance(cmdclass, dict):
        raise ValueError("cmdclass must be a dict")

    if eggs is None:
        eggs = []
    if not isinstance(eggs, list):
        raise ValueError("eggs must be a list")

    egg = "{name}*.egg-info".format(
        name=pkg_resources.to_filename(pkg_resources.safe_name(name))
    )
    if egg not in eggs:
        eggs = [egg] + eggs

    cmdclass.update(
        {
            "clean": CleanCommand.for_options(
                source_folder=os.path.join(source_folder, package), eggs=eggs
            )
        }
    )

    translation_dir = os.path.join(source_folder, "translations")
    pot_file = os.path.join(translation_dir, "messages.pot")
    bundled_dir = os.path.join(source_folder, package, "translations")
    cmdclass.update(
        get_babel_commandclasses(
            pot_file=pot_file,
            output_dir=translation_dir,
            bundled_dir=bundled_dir,
            pack_name_prefix="{name}-i18n-".format(**locals()),
            pack_path_prefix="_plugins/{identifier}/".format(**locals()),
        )
    )

    from setuptools import find_packages

    packages = set(
        [package]
        + list(
            filter(
                lambda x: x.startswith("{package}.".format(package=package)),
                find_packages(where=source_folder, exclude=ignored_packages),
            )
        )
        + additional_packages
    )
    print("Found packages: {packages!r}".format(**locals()))

    return {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "author_email": mail,
        "url": url,
        "license": license,
        # adding new commands
        "cmdclass": cmdclass,
        # we only have our plugin package to install
        "packages": packages,
        # we might have additional data files in sub folders that need to be installed too
        "package_data": {
            package: package_data_dirs(
                os.path.join(source_folder, package),
                ["static", "templates", "translations"] + additional_data,
            )
        },
        "include_package_data": True,
        # If you have any package data that needs to be accessible on the file system, such as templates or static assets
        # this plugin is not zip_safe.
        "zip_safe": False,
        "install_requires": requires,
        "extras_require": extra_requires,
        "dependency_links": dependency_links,
        # Hook the plugin into the "octoprint.plugin" entry point, mapping the plugin_identifier to the plugin_package.
        # That way OctoPrint will be able to find the plugin and load it.
        "entry_points": {
            "octoprint.plugin": ["{identifier} = {package}".format(**locals())]
        },
    }
