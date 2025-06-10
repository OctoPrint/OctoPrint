__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import re
import sys

import click

click.disable_unicode_literals_warning = True


class OctoPrintDevelCommands(click.MultiCommand):
    """
    Custom `click.MultiCommand <http://click.pocoo.org/5/api/#click.MultiCommand>`_
    implementation that provides commands relevant for (plugin) development
    based on availability of development dependencies.
    """

    sep = ":"
    groups = ("plugin", "css")

    def __init__(self, *args, **kwargs):
        click.MultiCommand.__init__(self, *args, **kwargs)

        from functools import partial

        from octoprint.util.commandline import CommandlineCaller

        def log_util(f):
            def log(*lines):
                for line in lines:
                    f(line)

            return log

        self.command_caller = CommandlineCaller()
        self.command_caller.on_log_call = log_util(lambda x: click.echo(f">> {x}"))
        self.command_caller.on_log_stdout = log_util(click.echo)
        self.command_caller.on_log_stderr = log_util(partial(click.echo, err=True))

    def _get_prefix_methods(self, method_prefix):
        for name in [x for x in dir(self) if x.startswith(method_prefix)]:
            method = getattr(self, name)
            yield method

    def _get_commands_from_prefix_methods(self, method_prefix):
        for method in self._get_prefix_methods(method_prefix):
            result = method()
            if result is not None and isinstance(result, click.Command):
                yield result

    def _get_commands(self):
        result = {}
        for group in self.groups:
            for command in self._get_commands_from_prefix_methods(f"{group}_"):
                result[group + self.sep + command.name] = command
        return result

    def list_commands(self, ctx):
        result = list(self._get_commands())
        result.sort()
        return result

    def get_command(self, ctx, cmd_name):
        commands = self._get_commands()
        return commands.get(cmd_name, None)

    def plugin_new(self):
        try:
            import cookiecutter.main
        except ImportError:
            return None

        import contextlib

        @contextlib.contextmanager
        def custom_cookiecutter_config(config):
            """
            Allows overriding cookiecutter's user config with a custom dict
            with fallback to the original data.
            """
            from octoprint.util import fallback_dict

            original_get_user_config = cookiecutter.main.get_user_config
            try:

                def f(*args, **kwargs):
                    original_config = original_get_user_config(*args, **kwargs)
                    return fallback_dict(config, original_config)

                cookiecutter.main.get_user_config = f
                yield
            finally:
                cookiecutter.main.get_user_config = original_get_user_config

        @contextlib.contextmanager
        def custom_cookiecutter_prompt(options):
            """
            Custom cookiecutter prompter for the template config.

            If a setting is available in the provided options (read from the CLI)
            that will be used, otherwise the user will be prompted for a value
            via click.
            """
            original_prompt_for_config = cookiecutter.main.prompt_for_config

            def custom_prompt_for_config(context, no_input=False):
                from cookiecutter.environment import StrictEnvironment

                cookiecutter_dict = {}

                env = StrictEnvironment()

                for key, raw in context["cookiecutter"].items():
                    if key in options:
                        val = options[key]
                    else:
                        if not isinstance(raw, str):
                            raw = str(raw)
                        val = env.from_string(raw).render(cookiecutter=cookiecutter_dict)

                        if not no_input:
                            val = click.prompt(key, default=val)

                    cookiecutter_dict[key] = val
                return cookiecutter_dict

            try:
                cookiecutter.main.prompt_for_config = custom_prompt_for_config
                yield
            finally:
                cookiecutter.main.prompt_for_config = original_prompt_for_config

        @click.command("new")
        @click.option("--name", "-n", help="The name of the plugin")
        @click.option("--package", "-p", help="The plugin package")
        @click.option("--author", "-a", help="The plugin author's name")
        @click.option("--email", "-e", help="The plugin author's mail address")
        @click.option("--license", "-l", help="The plugin's license")
        @click.option("--description", "-d", help="The plugin's description")
        @click.option("--homepage", help="The plugin's homepage URL")
        @click.option("--source", "-s", help="The URL to the plugin's source")
        @click.option("--installurl", "-i", help="The plugin's install URL")
        @click.argument("identifier", required=False)
        def command(
            name,
            package,
            author,
            email,
            description,
            license,
            homepage,
            source,
            installurl,
            identifier,
        ):
            """Creates a new plugin based on the OctoPrint Plugin cookiecutter template."""
            from octoprint.util import tempdir

            # deleting a git checkout folder might run into access errors due
            # to write-protected sub folders, so we use a custom onerror handler
            # that tries to fix such permissions
            def onerror(func, path, exc_info):
                """Originally from http://stackoverflow.com/a/2656405/2028598"""
                import os
                import stat

                if not os.access(path, os.W_OK):
                    os.chmod(path, stat.S_IWUSR)
                    func(path)
                else:
                    raise

            with tempdir(onerror=onerror) as path:
                custom = {"cookiecutters_dir": path}
                with custom_cookiecutter_config(custom):
                    raw_options = {
                        "plugin_identifier": identifier,
                        "plugin_package": package,
                        "plugin_name": name,
                        "full_name": author,
                        "email": email,
                        "plugin_description": description,
                        "plugin_license": license,
                        "plugin_homepage": homepage,
                        "plugin_source": source,
                        "plugin_installurl": installurl,
                    }
                    options = {k: v for k, v in raw_options.items() if v is not None}

                    with custom_cookiecutter_prompt(options):
                        cookiecutter.main.cookiecutter(
                            "gh:OctoPrint/cookiecutter-octoprint-plugin"
                        )

        return command

    def plugin_install(self):
        @click.command("install")
        @click.option(
            "--path", help="Path of the local plugin development folder to install"
        )
        def command(path):
            """
            Installs the local plugin in development mode.

            Note: This can NOT be used to install plugins from remote locations
            such as the plugin repository! It is strictly for local development
            of plugins, to ensure the plugin is installed (editable) into the
            same python environment that OctoPrint is installed under.
            """

            import os

            if not path:
                path = os.getcwd()

            has_setup_py = os.path.isfile(os.path.join(path, "setup.py"))
            has_pyproject_toml = os.path.isfile(os.path.join(path, "pyproject.toml"))

            # check if this really looks like a plugin
            if not has_setup_py and not has_pyproject_toml:
                click.echo("This doesn't look like an OctoPrint plugin folder")
                sys.exit(1)

            args = [sys.executable, "-m", "pip", "install", "-e", "."]
            if not has_pyproject_toml:
                click.echo(
                    "No pyproject.toml detected, adding --use-pep517 and --no-build-isolation to the pip call to improve compatibility with modern tooling..."
                )
                args += ["--use-pep517", "--no-build-isolation"]

            self.command_caller.call(
                args,
                cwd=path,
            )

        return command

    def plugin_uninstall(self):
        @click.command("uninstall")
        @click.argument("name")
        def command(name):
            """Uninstalls the plugin with the given name."""

            lower_name = name.lower()
            if not lower_name.startswith("octoprint_") and not lower_name.startswith(
                "octoprint-"
            ):
                click.echo("This doesn't look like an OctoPrint plugin name")
                sys.exit(1)

            call = [sys.executable, "-m", "pip", "uninstall", "--yes", name]
            self.command_caller.call(call)

        return command

    def plugin_migrate_to_pyproject(self):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # Python < 3.11

        try:
            import tomli_w
        except ImportError:
            return None

        @click.command("migrate-to-pyproject")
        @click.option(
            "--path", help="Path of the local plugin development folder to migrate"
        )
        @click.option(
            "--force",
            "force",
            is_flag=True,
            help="Force migration, even if setup.py looks wrong",
        )
        def command(path, force):
            """
            Migrates a plugin based on OctoPrint's setup.py template to the use of pyproject.toml and a Taskfile
            """

            import os
            from typing import Any

            from octoprint.util.files import search_through_file

            if not path:
                path = os.getcwd()

            setup_py = os.path.join(path, "setup.py")
            has_setup_py = os.path.isfile(setup_py)
            if not has_setup_py:
                click.echo("No setup.py found")
                sys.exit(1)

            if not force and not search_through_file(
                setup_py, "import octoprint_setuptools"
            ):
                click.echo(
                    "This doesn't look like a plugin based on OctoPrint's setup.py template"
                )
                sys.exit(1)

            TASKFILE_TEMPLATE_HEADER = """
# https://taskfile.dev

version: "3"

env:
LOCALES: {plugin_locales}  # list your included locales here, e.g. ["de", "fr"]
TRANSLATIONS: "{plugin_package}/translations"  # translations folder, do not touch

"""

            TASKFILE_TEMPLATE_BODY = """
tasks:
install:
    desc: Installs the plugin into the current venv
    cmds:
    - "python -m pip install -e .[develop]"

### Build related

build:
    desc: Builds sdist & wheel
    cmds:
    - python -m build --sdist --wheel

build-sdist:
    desc: Builds sdist
    cmds:
    - python -m build --sdist

build-wheel:
    desc: Builds wheel
    cmds:
    - python -m build --wheel

### Translation related

babel-new:
    desc: Create a new translation for a locale
    cmds:
    - task: babel-extract
    - |
        pybabel init --input-file=translations/messages.pot --output-dir=translations --locale="{{ .CLI_ARGS }}"

babel-extract:
    desc: Update pot file from source
    cmds:
    - pybabel extract --mapping-file=babel.cfg --output-file=translations/messages.pot --msgid-bugs-address=i18n@octoprint.org --copyright-holder="The OctoPrint Project" .

babel-update:
    desc: Update translation files from pot file
    cmds:
    - for:
        var: LOCALES
        cmd: pybabel update --input-file=translations/messages.pot --output-dir=translations --locale={{ .ITEM }}

babel-refresh:
    desc: Update translation files from source
    cmds:
    - task: babel-extract
    - task: babel-update

babel-compile:
    desc: Compile translation files
    cmds:
    - pybabel compile --directory=translations

babel-bundle:
    desc: Bundle translations
    preconditions:
    - test -d {{ .TRANSLATIONS }}
    cmds:
    - for:
        var: LOCALES
        cmd: |
        locale="{{ .ITEM }}"
        source="translations/${locale}"
        target="{{ .TRANSLATIONS }}/${locale}"

        [ ! -d "${target}" ] || rm -r "${target}"

        echo "Copying translations for locale ${locale} from ${source} to ${target}..."
        cp -r "${source}" "${target}"
"""

            REQUIRED_PLUGIN_DATA = [
                "plugin_identifier",
                "plugin_package",
                "plugin_name",
                "plugin_version",
                "plugin_description",
                "plugin_author",
                "plugin_author_email",
                "plugin_url",
                "plugin_license",
                "plugin_requires",
                "plugin_additional_data",
                "plugin_additional_packages",
                "plugin_ignored_packages",
            ]
            EXPECTED_PLUGIN_DATA = REQUIRED_PLUGIN_DATA + [
                "additional_setup_parameters",
            ]

            def _extract_plugin_data_from_setup_py(setup_py: str) -> dict[str, Any]:
                import ast

                click.echo(f"Extracting plugin data from {setup_py}...")

                with open(setup_py) as f:
                    contents = f.read()

                def ast_value(node) -> Any:
                    if isinstance(node, ast.Constant):
                        return node.value
                    elif isinstance(node, ast.List):
                        return [ast_value(entry) for entry in node.elts]
                    elif isinstance(node, ast.Dict):
                        return {
                            ast_value(key): ast_value(value)
                            for key, value in zip(node.keys, node.values)
                        }
                    else:
                        raise ValueError(f"Don't know how to parse {node!r}")

                plugin_data = {}
                mod = ast.parse(contents)
                for node in mod.body:
                    if (
                        isinstance(node, ast.Assign)
                        and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id in EXPECTED_PLUGIN_DATA
                    ):
                        field = str(node.targets[0].id)
                        plugin_data[field] = ast_value(node.value)

                if not all(key in plugin_data for key in REQUIRED_PLUGIN_DATA):
                    raise RuntimeError(
                        f"setup.py does not contain all required keys, can't migrate. Required: {', '.join(REQUIRED_PLUGIN_DATA)}"
                    )

                return plugin_data

            def _validate_and_migrate_plugin_data(
                folder: str, plugin_data: dict[str, Any]
            ):
                click.echo("Validating and migrating plugin data...")

                # name
                try:
                    plugin_data["plugin_name"] = _get_pep508_name(
                        plugin_data["plugin_name"]
                    )
                except ValueError as err:
                    raise RuntimeError(
                        "Project name is not PEP508 compliant and cannot automatically "
                        "be converted. Please rename your plugin manually to match PEP508. "
                        "See https://packaging.python.org/en/latest/specifications/name-normalization/ for details."
                    ) from err

                # license
                plugin_data["plugin_license"] = _get_spdx_license(
                    plugin_data["plugin_license"]
                )

                # python requires
                plugin_data["plugin_python_requires"] = ">=3.7,<4"
                if (
                    "additional_setup_parameters" in plugin_data
                    and "python_requires" in plugin_data["additional_setup_parameters"]
                ):
                    plugin_data["plugin_python_requires"] = plugin_data[
                        "additional_setup_parameters"
                    ]["python_requires"]

                # locales
                plugin_data["plugin_locales"] = []
                translation_folder = os.path.join(folder, "translations")
                if os.path.isdir(translation_folder):
                    import pathlib

                    plugin_data["plugin_locales"] = [
                        x
                        for x in pathlib.Path(translation_folder).iterdir()
                        if x.is_dir()
                    ]

            def _generate_pyproject_toml(
                folder: str, plugin_data: dict[str, Any]
            ) -> None:
                pyproject_toml = os.path.join(folder, "pyproject.toml")
                click.echo(f"Generating {pyproject_toml}...")

                doc = {}
                doc["build-system"] = {
                    "requires": ["setuptools>=67", "wheel"],
                    "build-backend": "setuptools.build_meta",
                }
                doc["project"] = {
                    "name": plugin_data["plugin_name"],
                    "version": plugin_data["plugin_version"],
                    "description": plugin_data["plugin_description"],
                    "authors": [
                        {
                            "name": plugin_data["plugin_author"],
                            "email": plugin_data["plugin_author_email"],
                        }
                    ],
                    "license": plugin_data["plugin_license"],
                    "requires-python": plugin_data["plugin_python_requires"],
                    "dependencies": plugin_data["plugin_requires"],
                    "entry-points": {
                        "octoprint.plugin": {
                            plugin_data["plugin_identifier"]: plugin_data[
                                "plugin_package"
                            ]
                        },
                    },
                    "urls": {"Homepage": plugin_data["plugin_url"]},
                    "optional-dependencies": {"develop": ["go-task-bin"]},
                }

                doc["tool"] = {
                    "setuptools": {
                        "include-package-data": True,
                        "packages": [plugin_data["plugin_package"]],
                    }
                }

                if os.path.isfile(os.path.join(path, "README.md")):
                    doc["project"]["readme"] = {
                        "file": "README.md",
                        "content-type": "markdown",
                    }

                if os.path.isfile(pyproject_toml):
                    # pyproject.toml already exists, so let's merge things
                    from octoprint.util import dict_merge

                    click.echo("\tFound an existing pyproject.toml, merging...")
                    with open(pyproject_toml, mode="rb") as f:
                        data = tomllib.load(f)

                    doc = dict_merge(doc, data)

                # ensure we are producing valid toml
                try:
                    tomllib.loads(tomli_w.dumps(doc))
                except tomllib.TOMLDecodeError:
                    click.echo(
                        "Something went wrong here, generated TOML is invalid",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                with open(pyproject_toml, "wb") as f:
                    tomli_w.dump(doc, f)

            def _generate_taskfile(folder: str, plugin_data: dict[str, Any]) -> None:
                taskfile = os.path.join(folder, "Taskfile.yml")
                click.echo(f"Generating {taskfile}...")

                with open(taskfile, mode="w") as f:
                    f.write(TASKFILE_TEMPLATE_HEADER.format(**plugin_data))
                    f.write(TASKFILE_TEMPLATE_BODY)

            def _cleanup_setup_cfg(setup_cfg: str) -> bool:
                import configparser

                if not os.path.isfile(setup_cfg):
                    return True

                config = configparser.ConfigParser()
                try:
                    config.read(setup_cfg)
                except configparser.ParsingError as exc:
                    click.echo(
                        f"Parsing error while reading {setup_cfg}: {exc}", file=sys.stderr
                    )
                    return False

                if "bdist_wheel" in config:
                    # remove `bdist_wheel.universal = 1` declaration, if it's there
                    try:
                        del config["bdist_wheel"]["universal"]
                    except KeyError:
                        pass

                    if not len(config["bdist_wheel"]):
                        del config["bdist_wheel"]

                if len(config):
                    # there's more in here
                    with open(setup_cfg, "w") as f:
                        config.write(f)
                    return False

                return True

            def _cleanup(folder: str) -> None:
                click.echo("Cleaning up...")

                deprecated = ["setup.py", "requirements.txt"]
                for d in deprecated:
                    path = os.path.join(folder, d)
                    if os.path.isfile(path):
                        click.echo(f"\tRemoving no longer needed {path}...")
                        os.remove(path)

                setup_cfg = os.path.join(folder, "setup.cfg")
                if not _cleanup_setup_cfg(setup_cfg):
                    click.echo(
                        "\tWARNING: Not removing {setup_cfg}, there might still be important tool settings in there"
                    )
                else:
                    click.echo("\tRemoving no longer needed {setup_cfg}...")
                    os.remove("setup.cfg")

            plugin_data = _extract_plugin_data_from_setup_py(setup_py)
            _validate_and_migrate_plugin_data(path, plugin_data)
            _generate_pyproject_toml(path, plugin_data)
            _generate_taskfile(path, plugin_data)
            _cleanup(path)

            click.echo("... done!")

        return command

    def css_build(self):
        @click.command("build")
        @click.option(
            "--file",
            "-f",
            "files",
            multiple=True,
            help="Specify files to build, for a list of options use --list",
        )
        @click.option("--all", "all_files", is_flag=True, help="Build all less files")
        @click.option(
            "--list",
            "list_files",
            is_flag=True,
            help="List all available files and exit",
        )
        def command(files, all_files, list_files):
            available_files = self._get_available_less_files()

            if list_files:
                click.echo("Available files to build:")
                for name in available_files.keys():
                    click.echo(f"- {name}")
                sys.exit(0)

            if all_files:
                files = available_files.keys()

            if not files:
                click.echo(
                    "No files specified. Use `--file <file>` to specify individual files, or `--all` to build all."
                )
                sys.exit(1)

            less = self._get_lessc()

            for less_file in files:
                file_data = available_files.get(less_file)
                if file_data is None:
                    click.echo(f"Unknown file {less_file}")
                    sys.exit(1)

                self._run_lessc(
                    less,
                    file_data["source"],
                    file_data["output"],
                )

        return command

    def css_watch(self):
        @click.command("watch")
        @click.option(
            "--file",
            "-f",
            "files",
            multiple=True,
            help="Specify files to watch & build, for a list of options use --list",
        )
        @click.option(
            "--all", "all_files", is_flag=True, help="Watch & build all less files"
        )
        @click.option(
            "--list",
            "list_files",
            is_flag=True,
            help="List all available files and exit",
        )
        def command(files, all_files, list_files):
            import os
            import time

            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            available_files = self._get_available_less_files()

            if list_files:
                click.echo("Available files to build:")
                for name in available_files.keys():
                    click.echo(f"- {name}")
                sys.exit(0)

            if all_files:
                files = available_files.keys()

            if not files:
                click.echo(
                    "No files specified. Use `--file <file>` to specify individual files, or `--all` to build all."
                )
                sys.exit(1)

            lessc = self._get_lessc()

            class LesscEventHandler(FileSystemEventHandler):
                def __init__(self, files, compiler):
                    super().__init__()
                    self._files = files
                    self._compiler = compiler

                def dispatch(self, event):
                    if event.is_directory:
                        return

                    path = os.fsdecode(event.src_path)
                    if path in self._files.keys():
                        super().dispatch(event)

                def on_modified(self, event):
                    less_file = os.fsdecode(event.src_path)

                    click.echo(
                        f"\nModification of {less_file} detected, compiling to CSS..."
                    )

                    css_file = self._files[less_file]
                    self._compiler(less_file, css_file)

            octoprint_base = str(self._get_octoprint_base())
            selected = {
                v["source"]: v["output"] for k, v in available_files.items() if k in files
            }
            compiler = lambda l, c: self._run_lessc(lessc, l, c)
            handler = LesscEventHandler(selected, compiler)

            observer = Observer()
            observer.schedule(handler, octoprint_base, recursive=True)
            observer.start()

            click.echo(f"Selected files: {', '.join(files)}")
            click.echo("Starting to watch selected files, hit Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

        return command

    def _get_octoprint_base(self):
        from pathlib import Path

        return Path(__file__).parent.parent

    def _get_available_less_files(self) -> dict:
        from pathlib import Path

        # src/octoprint
        octoprint_base = self._get_octoprint_base()

        available_files = {}
        for less_file in Path(octoprint_base, "static", "less").glob("*.less"):
            # Check corresponding css file exists
            # Less files can be imported, not all need building
            css_file = Path(less_file.parent.parent, "css", f"{less_file.stem}.css")
            if css_file.exists():
                available_files[less_file.stem] = {
                    "source": str(less_file),
                    "output": str(css_file),
                }

        path_to_plugins = Path(octoprint_base, "plugins")
        for plugin in Path(path_to_plugins).iterdir():
            for less_file in Path(plugin, "static", "less").glob("*.less"):
                name = f"plugin_{plugin.name}"
                if less_file.stem != plugin.name:
                    name += f"_{less_file.stem}"
                # Check there is a corresponding CSS file first
                css_file = Path(less_file.parent.parent, "css", f"{less_file.stem}.css")
                if css_file.exists():
                    available_files[name] = {
                        "source": str(less_file),
                        "output": str(css_file),
                    }

        return available_files

    def _get_lessc(self):
        import shutil

        # Check that lessc is installed
        less = shutil.which("lessc")

        # Check that less-plugin-clean-css is installed
        if less:
            _, _, stderr = self.command_caller.call([less, "--clean-css"], logged=False)
            clean_css = not any("Unable to load plugin clean-css" in x for x in stderr)
        else:
            clean_css = False

        if not less or not clean_css:
            click.echo(
                "lessc or less-plugin-clean-css is not installed/not available, please install it first"
            )
            click.echo(
                "Try `npm i -g less less-plugin-clean-css` to install both (note that it does NOT say 'lessc' in this command!)"
            )
            sys.exit(1)

        return less

    def _run_lessc(self, lessc, source, target):
        # Build command line, with necessary options
        less_command = [
            lessc,
            "--clean-css=--s1 --advanced --compatibility=ie8",
            source,
            target,
        ]

        self.command_caller.call(less_command)


@click.group(cls=OctoPrintDevelCommands)
def cli():
    """Additional commands for development tasks."""
    pass


def _get_pep508_name(name: str) -> str:
    PROJECT_NAME_VALIDATOR = re.compile(
        r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", flags=re.IGNORECASE
    )

    PROJECT_NAME_INVALID = re.compile(r"[^A-Z0-9.-]", flags=re.IGNORECASE)

    if PROJECT_NAME_VALIDATOR.match(name):
        return name

    name = PROJECT_NAME_INVALID.sub("-", name)
    if not PROJECT_NAME_VALIDATOR.match(name):
        raise ValueError(f"{name} is not PEP508 compliant")

    return name


def _get_spdx_license(license: str) -> str:
    SPDX_LICENSE_LUT = {
        "agpl-3.0": "AGPL-3.0-or-later",
        "agplv3": "AGPL-3.0-or-later",
        "agpl v3": "AGPL-3.0-or-later",
        "apache 2": "Apache-2.0",
        "apache 2.0": "Apache-2.0",
        "apache-2.0": "Apache-2.0",
        "apache license 2.0": "Apache-2.0",
        "bsd-3-clause": "BSD-3-Clause",
        "cc by-nc-sa 4.0": "CC-BY-NC-SA-4.0",
        "cc by-nd": "CC-BY-ND-4.0",
        "gnu affero general public license": "LicenseRef-AGPL",
        "gnu general public license v3.0": "GPL-3.0-or-later",
        "gnuv3": "GPL-3.0-or-later",
        "gnu v3.0": "GPL-3.0-or-later",
        "gpl-3.0 license": "GPL-3.0-or-later",
        "gplv3": "GPL-3.0-or-later",
        "mit": "MIT",
        "mit license": "MIT",
        "unlicence": "Unlicense",
    }  # extracted from plugins.octoprint.org/plugins.json on 2025-06-05

    SPDX_IDSTRING_INVALID = re.compile(r"[^A-Z0-9.-]", flags=re.IGNORECASE)

    from packaging.licenses import (
        InvalidLicenseExpression,
        canonicalize_license_expression,
    )

    try:
        return canonicalize_license_expression(
            SPDX_LICENSE_LUT.get(
                license.lower(),
                license,
            )
        )
    except InvalidLicenseExpression:
        license = SPDX_IDSTRING_INVALID.sub("-", license)
        return f"LicenseRef-{license}"
