# OctoPrint documentation build configuration file

import os
import sys

sys.path.insert(0, os.path.abspath("../src/"))
sys.path.append(os.path.abspath("sphinxext"))

from datetime import date

from packaging.version import parse as parse_version

from octoprint import __version__ as octoprint_version

year_since = 2013
year_current = date.today().year

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = "8.2"

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    # ext
    "sphinx.ext.todo",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.httpdomain",
    "sphinxcontrib.autodoc_pydantic",
    # custom
    "codeblockext",
    "pydanticext",
    # theme
    "sphinx_immaterial",
    # markdown
    "myst_parser",
]
todo_include_todos = True
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pyserial": ("https://pythonhosted.org/pyserial", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "OctoPrint"
copyright = (
    "%d-%d, OctoPrint" % (year_since, year_current)
    if year_current > year_since
    else "%d, OctoPrint" % year_since
)

# The short X.Y version.
version = parse_version(octoprint_version).base_version

# The full version, including alpha/beta/rc tags.
release = version

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["_build"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "stata-dark"

numfig = True

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of built-in themes.
html_theme = "sphinx_immaterial"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "site_url": "https://docs.octoprint.org",
    "repo_url": "https://github.com/OctoPrint/OctoPrint",
    "repo_name": "OctoPrint/OctoPrint",
    # "version_dropdown": True,
    # "version_info": [
    #    {"version": "1.12.0", "title": "1.12.0", "aliases": ["maintenance"]},
    #    {"version": "1.11.1", "title": "1.11.1", "aliases": ["latest", "master"]},
    # ],
    "globaltoc_collapse": True,
    "features": [
        "navigation.expand",
        # "navigation.tabs",
        # "navigation.tabs.sticky",
        # "toc.integrate",
        "navigation.sections",
        # "navigation.instant",
        # "header.autohide",
        "navigation.top",
        "navigation.footer",
        # "navigation.tracking",
        # "search.highlight",
        "search.share",
        "search.suggest",
        "toc.follow",
        "toc.sticky",
        "content.tabs.link",
        "content.code.copy",
        "content.tooltips",
        "announce.dismiss",
    ],
    "palette": [
        {
            "media": "(prefers-color-scheme)",
            "toggle": {
                "icon": "material/brightness-auto",
                "name": "Switch to light mode",
            },
        },
        {
            "media": "(prefers-color-scheme: light)",
            "scheme": "default",
            "toggle": {
                "icon": "material/lightbulb",
                "name": "Switch to dark mode",
            },
        },
        {
            "media": "(prefers-color-scheme: dark)",
            "scheme": "slate",
            "toggle": {
                "icon": "material/lightbulb-outline",
                "name": "Switch to system preference",
            },
        },
    ],
    "version_dropdown": True,
    "version_json": "../versions.json",
}

html_static_path = ["_static"]


# MyST parser config options
myst_enable_extensions = [
    "deflist",
    "fieldlist",
    "smartquotes",
    "replacements",
    "strikethrough",
    "substitution",
    "tasklist",
    "attrs_inline",
    "attrs_block",
    "colon_fence",
]

myst_enable_checkboxes = True
myst_substitutions = {
    "role": "[role](#syntax/roles)",
}

# Myst parser's strikethrough plugin seems to think that sphinx-immaterial doesn't use
# HTML output (probably due to the custom translator mixin used).
suppress_warnings = ["myst.strikethrough"]

# pydantic autodoc options
autodoc_pydantic_model_show_config_summary = True
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_hide_paramlist = True


def setup(app):
    app.add_css_file("theme_overrides.css")
