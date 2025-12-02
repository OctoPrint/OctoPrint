from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def set_url_query_param(url: str, key: str, value: str) -> str:
    """
    Sets the provided key-value query parameter on the provided url and returns it.

    Examples:

    >>> set_url_query_param("/test/path", "key", "value")
    '/test/path?key=value'
    >>> set_url_query_param("https://example.com/test/path", "key", "value")
    'https://example.com/test/path?key=value'
    >>> set_url_query_param("/test/path?foo=bar", "key", "value")
    '/test/path?foo=bar&key=value'
    >>> set_url_query_param("/test/path?key=other", "key", "value")
    '/test/path?key=value'
    >>> set_url_query_param("/test/path?foo=bar&key=other", "key", "value")
    '/test/path?foo=bar&key=value'
    >>> set_url_query_param("/test/path?foo=bar&key=other&bar=foo", "key", "value")
    '/test/path?foo=bar&key=value&bar=foo'

    """
    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if not any(k for k, _ in query if k == key):
        query.append((key, value))
    else:
        query = [(key, value) if k == key else (k, v) for k, v in query]
    return urlunparse(parsed._replace(query=urlencode(query)))
