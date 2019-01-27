# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

def callback(*args, **kwargs):
	pass

__plugin_hooks__ = {
	"some.ordered.callback": (callback, 10)
}
