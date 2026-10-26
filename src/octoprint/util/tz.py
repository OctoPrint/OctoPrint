__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"

import datetime

LOCAL_TZ = datetime.datetime.now(datetime.UTC).astimezone().tzinfo
UTC_TZ = datetime.UTC


def is_timezone_aware(dt: datetime.datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None
