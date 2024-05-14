__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from typing import List, Optional

from octoprint.schema import BaseModel
from octoprint.vendor.with_attrs_docs import with_attrs_docs


@with_attrs_docs
class AccessControlConfig(BaseModel):
    salt: Optional[str] = None
    """Secret salt used for password hashing. **DO NOT TOUCH!** If changed you will no longer be able to log in with your existing accounts. Default unset, generated on first run."""

    userManager: str = "octoprint.access.users.FilebasedUserManager"
    """The user manager implementation to use for accessing user information. Currently only a filebased user manager is implemented which stores configured accounts in a YAML file (Default: `users.yaml` in the default configuration folder)."""

    groupManager: str = "octoprint.access.groups.FilebasedGroupManager"
    """The group manager implementation to use for accessing group information. Currently only a filebased user manager is implemented which stores configured groups in a YAML file (Default: `groups.yaml` in the default configuration folder)."""

    permissionManager: str = "octoprint.access.permissions.PermissionManager"
    """The permission manager implementation to use."""

    userfile: Optional[str] = None
    """The YAML user file to use. If left out defaults to `users.yaml` in the default configuration folder."""

    groupfile: Optional[str] = None
    """The YAML group file to use. If left out defaults to `groups.yaml` in the default configuration folder."""

    autologinLocal: bool = False
    """If set to true, will automatically log on clients originating from any of the networks defined in `localNetworks` as the user defined in `autologinAs`."""

    localNetworks: List[str] = ["127.0.0.0/8", "::1/128"]
    """A list of networks or IPs for which an automatic logon as the user defined in `autologinAs` will take place. If available OctoPrint will evaluate the `X-Forwarded-For` HTTP header for determining the client's IP address. Defaults to anything originating from localhost."""

    autologinAs: Optional[str] = None
    """The name of the user to automatically log on clients originating from `localNetworks` as. Must be the name of one of your configured users."""

    autologinHeadsupAcknowledged: bool = False
    """Whether the user has acknowledged the heads-up about the importance of a correct reverse proxy configuration in the presence of autologin."""

    trustBasicAuthentication: bool = False
    """Whether to trust Basic Authentication headers. If you have setup Basic Authentication in front of OctoPrint and the user names you use there match OctoPrint accounts, by setting this to true users will be logged into OctoPrint as the user during Basic Authentication. **ONLY ENABLE THIS** if your OctoPrint instance is only accessible through a connection locked down through Basic Authentication!"""

    checkBasicAuthenticationPassword: bool = True
    """Whether to also check the password provided through Basic Authentication, if the Basic Authentication header is to be trusted. Disabling this will only match the user name in the Basic Authentication header and login the user without further checks, thus disable with caution."""

    trustRemoteUser: bool = False
    """Whether to trust remote user headers. If you have setup authentication in front of OctoPrint and the user names you use there match OctoPrint accounts, by setting this to true users will be logged into OctoPrint as the user provided in the header. **ONLY ENABLE THIS** if your OctoPrint instance is only accessible through a connection locked down through an authenticating reverse proxy!"""

    remoteUserHeader: str = "REMOTE_USER"
    """Header used by the reverse proxy to convey the authenticated user."""

    addRemoteUsers: bool = False
    """If a remote user is not found, add them. Use this only if all users from the remote system can use OctoPrint."""

    defaultReauthenticationTimeout: int = 5
    """Default timeout after which to require reauthentication by a user for dangerous changes, in minutes. Defaults to 5 minutes. Set to 0 to disable reauthentication requirements (SECURITY IMPACT!)."""
