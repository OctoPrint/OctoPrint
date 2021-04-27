# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse


class TornadoAccessFilter(logging.Filter):
    def filter(self, record):
        try:
            status, request_line, rtt = record.args

            if status == 409:

                method, url, client = request_line.split()
                u = urlparse.urlparse(url)
                if u.path in ("/api/printer",):
                    record.levelno = logging.INFO
                    record.levelname = logging.getLevelName(record.levelno)
        except Exception:
            logging.getLogger(__name__).exception(
                "Error while filtering log record {!r}".format(record)
            )

        return logging.Filter.filter(self, record)
