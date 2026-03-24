import html

import pytest

from octoprint.plugins.announcements import PLACEHOLDER_IMAGE

SAFE_FEED = """<rss version="2.0">
    <channel>
        <title>Safe Test Feed</title>
        <description>A safe test feed</description>
        <link>https://example.com/</link>
        <atom:link href="https://example.com/feed.xml" rel="self" type="application/rss+xml"/>
        <pubDate>Tue, 24 Mar 2026 11:46:26 +0000</pubDate>
        <lastBuildDate>Tue, 24 Mar 2026 11:46:26 +0000</lastBuildDate>
        <generator>Something 1.0.0</generator>
        <item>
            <title>Title <strong>with</strong> <em>tags</em>!</title>
            <description>
                <p>Summary with some HTML, e.g. <a href="https://example.com">a link</a>, some <strong>strong</strong> and some <em>em</em> markup and also an image: <img src="image.png" /></p>
            </description>
            <pubDate> Fri, 20 Feb 2026 00:00:00 +0000</pubDate>
            <link>
                https://example.com/link
            </link>
            <guid isPermaLink="true">
                https://example.com/link
            </guid>
            <category>cat1</category>
            <category>cat2</category>
        </item>
    </channel>
</rss>
"""

RSS_TEMPLATE = """<rss version="2.0">
    <channel>
        <title>Malicious RSS Feed</title>
        <description>A malicious RSS feed</description>
        <link>https://example.com/</link>
        <atom:link href="https://example.com/feed.xml" rel="self" type="application/rss+xml"/>
        <pubDate>Tue, 24 Mar 2026 11:46:26 +0000</pubDate>
        <lastBuildDate>Tue, 24 Mar 2026 11:46:26 +0000</lastBuildDate>
        <generator>Something 1.0.0</generator>
        <item>
            <title>Title</title>
            <description>{description}</description>
            <pubDate> Fri, 20 Feb 2026 00:00:00 +0000</pubDate>
            <link>
                https://example.com/link
            </link>
            <guid isPermaLink="true">
                https://example.com/link
            </guid>
            <category>cat1</category>
            <category>cat2</category>
        </item>
    </channel>
</rss>
"""

ATOM_TEMPLATE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Malicious Atom Feed</title><updated>2026-03-24T12:00:00Z</updated><id>urn:poc</id>
  <entry>
    <title>xlink:href bypass</title>
    <link href="http://x"/>
    <id>urn:1</id>
    <updated>2026-03-24T12:00:00Z</updated>
    <published>2026-03-24T12:00:00Z</published>
    <summary type="html">{description}</summary>
  </entry>
</feed>
"""

TEMPLATES = {"rss": RSS_TEMPLATE, "atom": ATOM_TEMPLATE}

MALICIOUS_TESTS = [
    ("""Test <script>alert(1)</script> 123""", "Test 123", "script"),
    (
        """Test <iframe onload="alert(1)" style="display:none"></iframe> 123""",
        "Test 123",
        "iframe onload",
    ),
    (
        """Test <img src="x" onerror=alert(1)> 123""",
        f"""Test <img src="{PLACEHOLDER_IMAGE}" data-src="x"> 123""",
        "img onerror, quoted",
    ),
    (
        """Test <img src=x onerror=alert(1)> 123""",
        f"""Test <img src="{PLACEHOLDER_IMAGE}" data-src="x"> 123""",
        "img onerror, unquoted",
    ),
    (
        """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="javascript:alert(&#39;XSS:xlink:href&#39;)"><text y="15">Click here</text></a></svg>""",
        """<a>Click here</a>""",
        "xlink:href bypass",
    ),
    (
        """<a href="&#x6A;avascript:alert(&#39;XSS:entity-href&#39;)">Click here</a>""",
        """<a href="#">Click here</a>""",
        "entity href",
    ),
    (
        """<form action="javascript:alert(&#39;XSS:form-action&#39;)"><button type="submit">Click here</button></form>""",
        "<p>Click here</p>",
        "form action",
    ),
]


def generate_malicious_tests():
    tests = []
    for feed in ("rss", "atom"):
        template = TEMPLATES.get(feed)
        for description, expected, testid in MALICIOUS_TESTS:
            tests += [
                pytest.param(
                    template, description, expected, id=f"{testid}|{feed}|plain"
                ),
                pytest.param(
                    template,
                    html.escape(description),
                    expected,
                    id=f"{testid}|{feed}|escaped",
                ),
            ]
    return tests


def test_to_internal_feed_basic(plugin):
    import feedparser

    feed = feedparser.parse(SAFE_FEED)

    internal = plugin._to_internal_feed(feed)

    assert len(internal) == 1

    entry = internal[0]
    assert entry["title"] == "Title <strong>with</strong> <em>tags</em>!"
    assert entry["title_without_tags"] == "Title with tags!"
    assert (
        entry["summary"]
        == f"""<p>Summary with some HTML, e.g. <a href="https://example.com">a link</a>, some <strong>strong</strong> and some <em>em</em> markup and also an image: <img src="{PLACEHOLDER_IMAGE}" data-src="image.png"></p>"""
    )
    assert (
        entry["summary_without_images"]
        == """<p>Summary with some HTML, e.g. <a href="https://example.com">a link</a>, some <strong>strong</strong> and some <em>em</em> markup and also an image: </p>"""
    )
    assert entry["link"].startswith(
        "https://example.com/link?utm_source=octoprint&utm_medium=announcements&utm_content="
    )
    assert "published" in entry
    assert entry["read"]


@pytest.mark.parametrize("feed,description,expected", generate_malicious_tests())
def test_to_internal_feed_sanitization(plugin, feed, description, expected):
    import feedparser

    feed = feedparser.parse(feed.format(description=description))

    internal = plugin._to_internal_feed(feed)

    assert len(internal) == 1

    entry = internal[0]
    assert entry["summary"] == expected
