# coding=utf-8
from .comm import MachineCom

__plugin_name__ = "Basic Comm"
__plugin_author__ = "Scott Lemmon, based on work by Gina Häußge"
__plugin_homepage__ = "https://github.com/authentise/OctoPrint/"
__plugin_license__ = "AGPLv3"
__plugin_description__ = "Provides the default comm object for OctoPrint to use for communicating with the printing"
__plugin_implementation__ = MachineCom()
