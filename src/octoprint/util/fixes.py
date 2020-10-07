# -*- coding: utf-8 -*-
"""
This module contains a functions that monkey patch third party dependencies in the one or other way.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

import functools
import sys
import warnings


def patch_sarge_async_on_py2():
    if sys.version_info[0] >= 3:
        return

    def move_async(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if "async" in kwargs:
                warnings.warn(
                    'sarge\'s "async" parameter is deprecated. Use "_async" instead.',
                    DeprecationWarning,
                    stacklevel=2,
                )
                kwargs["async_"] = kwargs.pop("async")
            return f(*args, **kwargs)

        return decorated_function

    import sarge

    # wrap helper
    sarge.run = move_async(sarge.run)

    # wrap Command
    sarge.Command.run = move_async(sarge.Command.run)

    # wrap Pipeline
    sarge.Pipeline.run = move_async(sarge.Pipeline.run)
    sarge.Pipeline.run_command_node = move_async(sarge.Pipeline.run_command_node)
    sarge.Pipeline.run_list_node = move_async(sarge.Pipeline.run_list_node)
    sarge.Pipeline.run_logical_node = move_async(sarge.Pipeline.run_logical_node)
    sarge.Pipeline.run_node = move_async(sarge.Pipeline.run_node)
    sarge.Pipeline.run_node_in_thread = move_async(sarge.Pipeline.run_node_in_thread)
    sarge.Pipeline.run_pipeline_node = move_async(sarge.Pipeline.run_pipeline_node)
