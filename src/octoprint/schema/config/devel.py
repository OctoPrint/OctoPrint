__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum

from pydantic import BaseModel

from octoprint.vendor.with_attrs_docs import with_attrs_docs


class StylesheetEnum(str, Enum):
    css = "css"
    less = "less"


@with_attrs_docs
class DevelWebassetsConfig(BaseModel):
    bundle: bool = True
    """If set to true, OctoPrint will merge all JS, all CSS and all Less files into one file per type to reduce request count. Setting it to false will load all assets individually. Note: if this is set to false, no minification will take place regardless of the `minify` setting."""

    clean_on_startup: bool = True
    """Whether to delete generated web assets on server startup (forcing a regeneration)."""

    minify: bool = True
    """If set to true, OctoPrint will the core and library javascript assets. Note: if `bundle` is set to false, no minification will take place either."""

    minify_plugins: bool = False
    """If set to true, OctoPrint will also minify the third party plugin javascript assets. Note: if `bundle` or `minify` are set to false, no minification of the plugin assets will take place either."""


class DevelCacheConfig(BaseModel):
    enabled: bool = True
    """Whether to enable caching. Defaults to true. Setting it to false will cause the UI to always be fully rerendered on request to `/` on the server."""

    preemptive: bool = True
    """Whether to enable the preemptive cache."""


@with_attrs_docs
class DevelConfig(BaseModel):
    stylesheet: StylesheetEnum = "css"
    """Settings for stylesheet preference. OctoPrint will prefer to use the stylesheet type specified here. Usually (on a production install) that will be the compiled css (default). Developers may specify less here too."""

    cache: DevelCacheConfig = DevelCacheConfig()
    """Settings for OctoPrint's internal caching."""

    webassets: DevelWebassetsConfig = DevelWebassetsConfig()
    """Settings for OctoPrint's web asset merging and minifying."""

    useFrozenDictForPrinterState: bool = True

    showLoadingAnimation: bool = True
    """Enable or disable the loading animation."""

    sockJsConnectTimeout: float = 30
    pluginTimings: bool = False

    enableRateLimiter: bool = True
    """Enable or disable the rate limiter. Careful, disabling this reduces security."""

    enableCsrfProtection: bool = True
    """Enable or disable the CSRF protection. Careful, disabling this reduces security."""
