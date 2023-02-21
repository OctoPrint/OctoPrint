import logging
import urllib.parse


class TornadoAccessFilter(logging.Filter):
    def filter(self, record):
        try:
            status, request_line, rtt = record.args

            if status == 409:
                _, url, _ = request_line.split()
                u = urllib.parse.urlparse(url)
                if u.path in ("/api/printer",):
                    record.levelno = logging.INFO
                    record.levelname = logging.getLevelName(record.levelno)
        except Exception:
            logging.getLogger(__name__).exception(
                f"Error while filtering log record {record!r}"
            )

        return logging.Filter.filter(self, record)
