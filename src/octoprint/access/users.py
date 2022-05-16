__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import hashlib
import logging
import os
import time
import uuid

import wrapt
from flask_login import AnonymousUserMixin, UserMixin
from werkzeug.local import LocalProxy

from octoprint.access.groups import Group, GroupChangeListener
from octoprint.access.permissions import OctoPrintPermission, Permissions
from octoprint.settings import settings as s
from octoprint.util import atomic_write, deprecated, generate_api_key
from octoprint.util import get_fully_qualified_classname as fqcn
from octoprint.util import to_bytes, yaml


class UserManager(GroupChangeListener):
    def __init__(self, group_manager, settings=None):
        self._group_manager = group_manager
        self._group_manager.register_listener(self)

        self._logger = logging.getLogger(__name__)
        self._session_users_by_session = {}
        self._sessionids_by_userid = {}

        if settings is None:
            settings = s()
        self._settings = settings

        self._login_status_listeners = []

    def register_login_status_listener(self, listener):
        self._login_status_listeners.append(listener)

    def unregister_login_status_listener(self, listener):
        self._login_status_listeners.remove(listener)

    def anonymous_user_factory(self):
        return AnonymousUser([self._group_manager.guest_group])

    def api_user_factory(self):
        return ApiUser([self._group_manager.admin_group, self._group_manager.user_group])

    @property
    def enabled(self):
        return True

    def login_user(self, user):
        self._cleanup_sessions()

        if user is None or user.is_anonymous:
            return

        if isinstance(user, LocalProxy):
            # noinspection PyProtectedMember
            user = user._get_current_object()

        if not isinstance(user, User):
            return None

        if not isinstance(user, SessionUser):
            user = SessionUser(user)

        self._session_users_by_session[user.session] = user

        userid = user.get_id()
        if userid not in self._sessionids_by_userid:
            self._sessionids_by_userid[userid] = set()

        self._sessionids_by_userid[userid].add(user.session)

        for listener in self._login_status_listeners:
            try:
                listener.on_user_logged_in(user)
            except Exception:
                self._logger.exception(
                    f"Error in on_user_logged_in on {listener!r}",
                    extra={"callback": fqcn(listener)},
                )

        self._logger.info(f"Logged in user: {user.get_id()}")

        return user

    def logout_user(self, user, stale=False):
        if user is None or user.is_anonymous:
            return

        if isinstance(user, LocalProxy):
            user = user._get_current_object()

        if not isinstance(user, SessionUser):
            return

        userid = user.get_id()
        sessionid = user.session

        if userid in self._sessionids_by_userid:
            try:
                self._sessionids_by_userid[userid].remove(sessionid)
            except KeyError:
                pass

        if sessionid in self._session_users_by_session:
            try:
                del self._session_users_by_session[sessionid]
            except KeyError:
                pass

        for listener in self._login_status_listeners:
            try:
                listener.on_user_logged_out(user, stale=stale)
            except Exception:
                self._logger.exception(
                    f"Error in on_user_logged_out on {listener!r}",
                    extra={"callback": fqcn(listener)},
                )

        self._logger.info(f"Logged out user: {user.get_id()}")

    def _cleanup_sessions(self):
        for session, user in list(self._session_users_by_session.items()):
            if not isinstance(user, SessionUser):
                continue
            if user.created + (24 * 60 * 60) < time.monotonic():
                self._logger.info(
                    "Cleaning up user session {} for user {}".format(
                        session, user.get_id()
                    )
                )
                self.logout_user(user, stale=True)

    @staticmethod
    def create_password_hash(password, salt=None, settings=None):
        if not salt:
            if settings is None:
                settings = s()
            salt = settings.get(["accessControl", "salt"])
            if salt is None:
                import string
                from random import choice

                chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
                salt = "".join(choice(chars) for _ in range(32))
                settings.set(["accessControl", "salt"], salt)
                settings.save()

        return hashlib.sha512(
            to_bytes(password, encoding="utf-8", errors="replace") + to_bytes(salt)
        ).hexdigest()

    def check_password(self, username, password):
        user = self.find_user(username)
        if not user:
            return False

        hash = UserManager.create_password_hash(password, settings=self._settings)
        if user.check_password(hash):
            # new hash matches, correct password
            return True
        else:
            # new hash doesn't match, but maybe the old one does, so check that!
            oldHash = UserManager.create_password_hash(
                password, salt="mvBUTvwzBzD3yPwvnJ4E4tXNf3CGJvvW", settings=self._settings
            )
            if user.check_password(oldHash):
                # old hash matches, we migrate the stored password hash to the new one and return True since it's the correct password
                self.change_user_password(username, password)
                return True
            else:
                # old hash doesn't match either, wrong password
                return False

    def add_user(self, username, password, active, permissions, groups, overwrite=False):
        pass

    def change_user_activation(self, username, active):
        pass

    def change_user_permissions(self, username, permissions):
        pass

    def add_permissions_to_user(self, username, permissions):
        pass

    def remove_permissions_from_user(self, username, permissions):
        pass

    def change_user_groups(self, username, groups):
        pass

    def add_groups_to_user(self, username, groups):
        pass

    def remove_groups_from_user(self, username, groups):
        pass

    def remove_groups_from_users(self, group):
        pass

    def change_user_password(self, username, password):
        pass

    def get_user_setting(self, username, key):
        return None

    def get_all_user_settings(self, username):
        return {}

    def change_user_setting(self, username, key, value):
        pass

    def change_user_settings(self, username, new_settings):
        pass

    def remove_user(self, username):
        if username in self._sessionids_by_userid:
            sessions = self._sessionids_by_userid[username]
            for session in sessions:
                if session in self._session_users_by_session:
                    del self._session_users_by_session[session]
            del self._sessionids_by_userid[username]

    def validate_user_session(self, userid, session):
        if session in self._session_users_by_session:
            user = self._session_users_by_session[session]
            return userid == user.get_id()

        return False

    def find_user(self, userid=None, session=None):
        if session is not None and session in self._session_users_by_session:
            user = self._session_users_by_session[session]
            if userid is None or userid == user.get_id():
                return user

        return None

    def find_sessions_for(self, matcher):
        result = []
        for user in self.get_all_users():
            if matcher(user):
                try:
                    session_ids = self._sessionids_by_userid[user.get_id()]
                    for session_id in session_ids:
                        try:
                            result.append(self._session_users_by_session[session_id])
                        except KeyError:
                            # unknown session after all
                            continue
                except KeyError:
                    # no session for user
                    pass
        return result

    def get_all_users(self):
        return []

    def has_been_customized(self):
        return False

    def on_group_removed(self, group):
        self._logger.debug(f"Group {group.key} got removed, removing from all users")
        self.remove_groups_from_users([group])

    def on_group_permissions_changed(self, group, added=None, removed=None):
        users = self.find_sessions_for(lambda u: group in u.groups)
        for listener in self._login_status_listeners:
            try:
                for user in users:
                    listener.on_user_modified(user)
            except Exception:
                self._logger.exception(
                    f"Error in on_user_modified on {listener!r}",
                    extra={"callback": fqcn(listener)},
                )

    def on_group_subgroups_changed(self, group, added=None, removed=None):
        users = self.find_sessions_for(lambda u: group in u.groups)
        for listener in self._login_status_listeners:
            # noinspection PyBroadException
            try:
                for user in users:
                    listener.on_user_modified(user)
            except Exception:
                self._logger.exception(
                    f"Error in on_user_modified on {listener!r}",
                    extra={"callback": fqcn(listener)},
                )

    def _trigger_on_user_modified(self, user):
        if isinstance(user, str):
            # user id
            users = []
            try:
                session_ids = self._sessionids_by_userid[user]
                for session_id in session_ids:
                    try:
                        users.append(self._session_users_by_session[session_id])
                    except KeyError:
                        # unknown session id
                        continue
            except KeyError:
                # no session for user
                return
        elif isinstance(user, User) and not isinstance(user, SessionUser):
            users = self.find_sessions_for(lambda u: u.get_id() == user.get_id())
        elif isinstance(user, User):
            users = [user]
        else:
            return

        for listener in self._login_status_listeners:
            try:
                for user in users:
                    listener.on_user_modified(user)
            except Exception:
                self._logger.exception(
                    f"Error in on_user_modified on {listener!r}",
                    extra={"callback": fqcn(listener)},
                )

    def _trigger_on_user_removed(self, username):
        for listener in self._login_status_listeners:
            try:
                listener.on_user_removed(username)
            except Exception:
                self._logger.exception(
                    f"Error in on_user_removed on {listener!r}",
                    extra={"callback": fqcn(listener)},
                )

    # ~~ Deprecated methods follow

    # TODO: Remove deprecated methods in OctoPrint 1.5.0

    @staticmethod
    def createPasswordHash(*args, **kwargs):
        """
        .. deprecated: 1.4.0

           Replaced by :func:`~UserManager.create_password_hash`
        """
        # we can't use the deprecated decorator here since this method is static
        import warnings

        warnings.warn(
            "createPasswordHash has been renamed to create_password_hash",
            DeprecationWarning,
            stacklevel=2,
        )
        return UserManager.create_password_hash(*args, **kwargs)

    @deprecated(
        "changeUserRoles has been replaced by change_user_permissions",
        includedoc="Replaced by :func:`change_user_permissions`",
        since="1.4.0",
    )
    def changeUserRoles(self, username, roles):
        user = self.find_user(username)
        if user is None:
            raise UnknownUser(username)

        removed_roles = set(user._roles) - set(roles)
        self.removeRolesFromUser(username, removed_roles, user=user)

        added_roles = set(roles) - set(user._roles)
        self.addRolesToUser(username, added_roles, user=user)

    @deprecated(
        "addRolesToUser has been replaced by add_permissions_to_user",
        includedoc="Replaced by :func:`add_permissions_to_user`",
        since="1.4.0",
    )
    def addRolesToUser(self, username, roles, user=None):
        if user is None:
            user = self.find_user(username)

        if user is None:
            raise UnknownUser(username)

        if "admin" in roles:
            self.add_groups_to_user(username, self._group_manager.admin_group)

        if "user" in roles:
            self.remove_groups_from_user(username, self._group_manager.user_group)

    @deprecated(
        "removeRolesFromUser has been replaced by remove_permissions_from_user",
        includedoc="Replaced by :func:`remove_permissions_from_user`",
        since="1.4.0",
    )
    def removeRolesFromUser(self, username, roles, user=None):
        if user is None:
            user = self.find_user(username)

        if user is None:
            raise UnknownUser(username)

        if "admin" in roles:
            self.remove_groups_from_user(username, self._group_manager.admin_group)
            self.remove_permissions_from_user(username, Permissions.ADMIN)

        if "user" in roles:
            self.remove_groups_from_user(username, self._group_manager.user_group)

    checkPassword = deprecated(
        "checkPassword has been renamed to check_password",
        includedoc="Replaced by :func:`check_password`",
        since="1.4.0",
    )(check_password)
    addUser = deprecated(
        "addUser has been renamed to add_user",
        includedoc="Replaced by :func:`add_user`",
        since="1.4.0",
    )(add_user)
    changeUserActivation = deprecated(
        "changeUserActivation has been renamed to change_user_activation",
        includedoc="Replaced by :func:`change_user_activation`",
        since="1.4.0",
    )(change_user_activation)
    changeUserPassword = deprecated(
        "changeUserPassword has been renamed to change_user_password",
        includedoc="Replaced by :func:`change_user_password`",
        since="1.4.0",
    )(change_user_password)
    getUserSetting = deprecated(
        "getUserSetting has been renamed to get_user_setting",
        includedoc="Replaced by :func:`get_user_setting`",
        since="1.4.0",
    )(get_user_setting)
    getAllUserSettings = deprecated(
        "getAllUserSettings has been renamed to get_all_user_settings",
        includedoc="Replaced by :func:`get_all_user_settings`",
        since="1.4.0",
    )(get_all_user_settings)
    changeUserSetting = deprecated(
        "changeUserSetting has been renamed to change_user_setting",
        includedoc="Replaced by :func:`change_user_setting`",
        since="1.4.0",
    )(change_user_setting)
    changeUserSettings = deprecated(
        "changeUserSettings has been renamed to change_user_settings",
        includedoc="Replaced by :func:`change_user_settings`",
        since="1.4.0",
    )(change_user_settings)
    removeUser = deprecated(
        "removeUser has been renamed to remove_user",
        includedoc="Replaced by :func:`remove_user`",
        since="1.4.0",
    )(remove_user)
    findUser = deprecated(
        "findUser has been renamed to find_user",
        includedoc="Replaced by :func:`find_user`",
        since="1.4.0",
    )(find_user)
    getAllUsers = deprecated(
        "getAllUsers has been renamed to get_all_users",
        includedoc="Replaced by :func:`get_all_users`",
        since="1.4.0",
    )(get_all_users)
    hasBeenCustomized = deprecated(
        "hasBeenCustomized has been renamed to has_been_customized",
        includedoc="Replaced by :func:`has_been_customized`",
        since="1.4.0",
    )(has_been_customized)


class LoginStatusListener:
    def on_user_logged_in(self, user):
        pass

    def on_user_logged_out(self, user, stale=False):
        pass

    def on_user_modified(self, user):
        pass

    def on_user_removed(self, userid):
        pass


##~~ FilebasedUserManager, takes available users from users.yaml file


class FilebasedUserManager(UserManager):
    def __init__(self, group_manager, path=None, settings=None):
        UserManager.__init__(self, group_manager, settings=settings)

        self._logger = logging.getLogger(__name__)

        if path is None:
            path = self._settings.get(["accessControl", "userfile"])
            if path is None:
                path = os.path.join(s().getBaseFolder("base"), "users.yaml")

        self._userfile = path

        self._users = {}
        self._dirty = False

        self._customized = None
        self._load()

    def _load(self):
        if os.path.exists(self._userfile) and os.path.isfile(self._userfile):
            data = yaml.load_from_file(path=self._userfile)

            if not data or not isinstance(data, dict):
                self._logger.fatal(
                    "{} does not contain a valid map of users. Fix "
                    "the file, or remove it, then restart OctoPrint.".format(
                        self._userfile
                    )
                )
                raise CorruptUserStorage()

            for name, attributes in data.items():
                if not isinstance(attributes, dict):
                    continue

                permissions = []
                if "permissions" in attributes:
                    permissions = attributes["permissions"]

                if "groups" in attributes:
                    groups = set(attributes["groups"])
                else:
                    groups = {self._group_manager.user_group}

                # migrate from roles to permissions
                if "roles" in attributes and "permissions" not in attributes:
                    self._logger.info(
                        f"Migrating user {name} to new granular permission system"
                    )

                    groups |= set(self._migrate_roles_to_groups(attributes["roles"]))
                    self._dirty = True

                apikey = None
                if "apikey" in attributes:
                    apikey = attributes["apikey"]
                settings = {}
                if "settings" in attributes:
                    settings = attributes["settings"]

                self._users[name] = User(
                    username=name,
                    passwordHash=attributes["password"],
                    active=attributes["active"],
                    permissions=self._to_permissions(*permissions),
                    groups=self._to_groups(*groups),
                    apikey=apikey,
                    settings=settings,
                )
                for sessionid in self._sessionids_by_userid.get(name, set()):
                    if sessionid in self._session_users_by_session:
                        self._session_users_by_session[sessionid].update_user(
                            self._users[name]
                        )

            if self._dirty:
                self._save()

            self._customized = True
        else:
            self._customized = False

    def _save(self, force=False):
        if not self._dirty and not force:
            return

        data = {}
        for name, user in self._users.items():
            if not user or not isinstance(user, User):
                continue

            data[name] = {
                "password": user._passwordHash,
                "active": user._active,
                "groups": self._from_groups(*user._groups),
                "permissions": self._from_permissions(*user._permissions),
                "apikey": user._apikey,
                "settings": user._settings,
                # TODO: deprecated, remove in 1.5.0
                "roles": user._roles,
            }

        with atomic_write(
            self._userfile, mode="wt", permissions=0o600, max_permissions=0o666
        ) as f:
            yaml.save_to_file(data, file=f, pretty=True)
            self._dirty = False
        self._load()

    def _migrate_roles_to_groups(self, roles):
        # If admin is inside the roles, just return admin group
        if "admin" in roles:
            return [self._group_manager.admin_group, self._group_manager.user_group]
        else:
            return [self._group_manager.user_group]

    def _refresh_groups(self, user):
        user._groups = self._to_groups(*map(lambda g: g.key, user.groups))

    def add_user(
        self,
        username,
        password,
        active=False,
        permissions=None,
        groups=None,
        apikey=None,
        overwrite=False,
    ):
        if not permissions:
            permissions = []
        permissions = self._to_permissions(*permissions)

        if not groups:
            groups = self._group_manager.default_groups
        groups = self._to_groups(*groups)

        if username in self._users and not overwrite:
            raise UserAlreadyExists(username)

        self._users[username] = User(
            username,
            UserManager.create_password_hash(password, settings=self._settings),
            active,
            permissions,
            groups,
            apikey=apikey,
        )
        self._dirty = True
        self._save()

    def change_user_activation(self, username, active):
        if username not in self._users:
            raise UnknownUser(username)

        if self._users[username].is_active != active:
            self._users[username]._active = active
            self._dirty = True
            self._save()

            self._trigger_on_user_modified(username)

    def change_user_permissions(self, username, permissions):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]

        permissions = self._to_permissions(*permissions)

        removed_permissions = list(set(user._permissions) - set(permissions))
        added_permissions = list(set(permissions) - set(user._permissions))

        if len(removed_permissions) > 0:
            user.remove_permissions_from_user(removed_permissions)
            self._dirty = True

        if len(added_permissions) > 0:
            user.add_permissions_to_user(added_permissions)
            self._dirty = True

        if self._dirty:
            self._save()
            self._trigger_on_user_modified(username)

    def add_permissions_to_user(self, username, permissions):
        if username not in self._users:
            raise UnknownUser(username)

        if self._users[username].add_permissions_to_user(
            self._to_permissions(*permissions)
        ):
            self._dirty = True
            self._save()
            self._trigger_on_user_modified(username)

    def remove_permissions_from_user(self, username, permissions):
        if username not in self._users:
            raise UnknownUser(username)

        if self._users[username].remove_permissions_from_user(
            self._to_permissions(*permissions)
        ):
            self._dirty = True
            self._save()
            self._trigger_on_user_modified(username)

    def remove_permissions_from_users(self, permissions):
        modified = []
        for user in self._users:
            dirty = user.remove_permissions_from_user(self._to_permissions(*permissions))
            if dirty:
                self._dirty = True
                modified.append(user.get_id())

        if self._dirty:
            self._save()
            for username in modified:
                self._trigger_on_user_modified(username)

    def change_user_groups(self, username, groups):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]

        groups = self._to_groups(*groups)

        removed_groups = list(set(user._groups) - set(groups))
        added_groups = list(set(groups) - set(user._groups))

        if len(removed_groups):
            self._dirty |= user.remove_groups_from_user(removed_groups)
        if len(added_groups):
            self._dirty |= user.add_groups_to_user(added_groups)

        if self._dirty:
            self._save()
            self._trigger_on_user_modified(username)

    def add_groups_to_user(self, username, groups, save=True, notify=True):
        if username not in self._users:
            raise UnknownUser(username)

        if self._users[username].add_groups_to_user(self._to_groups(*groups)):
            self._dirty = True

            if save:
                self._save()

            if notify:
                self._trigger_on_user_modified(username)

    def remove_groups_from_user(self, username, groups, save=True, notify=True):
        if username not in self._users:
            raise UnknownUser(username)

        if self._users[username].remove_groups_from_user(self._to_groups(*groups)):
            self._dirty = True

            if save:
                self._save()

            if notify:
                self._trigger_on_user_modified(username)

    def remove_groups_from_users(self, groups):
        modified = []
        for username, user in self._users.items():
            dirty = user.remove_groups_from_user(self._to_groups(*groups))
            if dirty:
                self._dirty = True
                modified.append(username)

        if self._dirty:
            self._save()

            for username in modified:
                self._trigger_on_user_modified(username)

    def change_user_password(self, username, password):
        if username not in self._users:
            raise UnknownUser(username)

        passwordHash = UserManager.create_password_hash(password, settings=self._settings)
        user = self._users[username]
        if user._passwordHash != passwordHash:
            user._passwordHash = passwordHash
            self._dirty = True
            self._save()

    def change_user_setting(self, username, key, value):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]
        old_value = user.get_setting(key)
        if not old_value or old_value != value:
            user.set_setting(key, value)
            self._dirty = self._dirty or old_value != value
            self._save()

    def change_user_settings(self, username, new_settings):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]
        for key, value in new_settings.items():
            old_value = user.get_setting(key)
            user.set_setting(key, value)
            self._dirty = self._dirty or old_value != value
        self._save()

    def get_all_user_settings(self, username):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]
        return user.get_all_settings()

    def get_user_setting(self, username, key):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]
        return user.get_setting(key)

    def generate_api_key(self, username):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]
        user._apikey = generate_api_key()
        self._dirty = True
        self._save()
        return user._apikey

    def delete_api_key(self, username):
        if username not in self._users:
            raise UnknownUser(username)

        user = self._users[username]
        user._apikey = None
        self._dirty = True
        self._save()

    def remove_user(self, username):
        UserManager.remove_user(self, username)

        if username not in self._users:
            raise UnknownUser(username)

        del self._users[username]
        self._dirty = True
        self._save()

    def find_user(self, userid=None, apikey=None, session=None):
        user = UserManager.find_user(self, userid=userid, session=session)

        if user is not None:
            return user

        if userid is not None:
            if userid not in self._users:
                return None
            return self._users[userid]

        elif apikey is not None:
            for user in self._users.values():
                if apikey == user._apikey:
                    return user
            return None

        else:
            return None

    def get_all_users(self):
        return list(self._users.values())

    def has_been_customized(self):
        return self._customized

    def on_group_permissions_changed(self, group, added=None, removed=None):
        # refresh our group references
        for user in self.get_all_users():
            if group in user.groups:
                self._refresh_groups(user)

        # call parent
        UserManager.on_group_permissions_changed(
            self, group, added=added, removed=removed
        )

    def on_group_subgroups_changed(self, group, added=None, removed=None):
        # refresh our group references
        for user in self.get_all_users():
            if group in user.groups:
                self._refresh_groups(user)

        # call parent
        UserManager.on_group_subgroups_changed(self, group, added=added, removed=removed)

    # ~~ Helpers

    def _to_groups(self, *groups):
        return list(
            set(
                filter(
                    lambda x: x is not None,
                    (self._group_manager._to_group(group) for group in groups),
                )
            )
        )

    def _to_permissions(self, *permissions):
        return list(
            set(
                filter(
                    lambda x: x is not None,
                    (Permissions.find(permission) for permission in permissions),
                )
            )
        )

    def _from_groups(self, *groups):
        return list({group.key for group in groups})

    def _from_permissions(self, *permissions):
        return list({permission.key for permission in permissions})

    # ~~ Deprecated methods follow

    # TODO: Remove deprecated methods in OctoPrint 1.5.0

    generateApiKey = deprecated(
        "generateApiKey has been renamed to generate_api_key",
        includedoc="Replaced by :func:`generate_api_key`",
        since="1.4.0",
    )(generate_api_key)
    deleteApiKey = deprecated(
        "deleteApiKey has been renamed to delete_api_key",
        includedoc="Replaced by :func:`delete_api_key`",
        since="1.4.0",
    )(delete_api_key)
    addUser = deprecated(
        "addUser has been renamed to add_user",
        includedoc="Replaced by :func:`add_user`",
        since="1.4.0",
    )(add_user)
    changeUserActivation = deprecated(
        "changeUserActivation has been renamed to change_user_activation",
        includedoc="Replaced by :func:`change_user_activation`",
        since="1.4.0",
    )(change_user_activation)
    changeUserPassword = deprecated(
        "changeUserPassword has been renamed to change_user_password",
        includedoc="Replaced by :func:`change_user_password`",
        since="1.4.0",
    )(change_user_password)
    getUserSetting = deprecated(
        "getUserSetting has been renamed to get_user_setting",
        includedoc="Replaced by :func:`get_user_setting`",
        since="1.4.0",
    )(get_user_setting)
    getAllUserSettings = deprecated(
        "getAllUserSettings has been renamed to get_all_user_settings",
        includedoc="Replaced by :func:`get_all_user_settings`",
        since="1.4.0",
    )(get_all_user_settings)
    changeUserSetting = deprecated(
        "changeUserSetting has been renamed to change_user_setting",
        includedoc="Replaced by :func:`change_user_setting`",
        since="1.4.0",
    )(change_user_setting)
    changeUserSettings = deprecated(
        "changeUserSettings has been renamed to change_user_settings",
        includedoc="Replaced by :func:`change_user_settings`",
        since="1.4.0",
    )(change_user_settings)
    removeUser = deprecated(
        "removeUser has been renamed to remove_user",
        includedoc="Replaced by :func:`remove_user`",
        since="1.4.0",
    )(remove_user)
    findUser = deprecated(
        "findUser has been renamed to find_user",
        includedoc="Replaced by :func:`find_user`",
        since="1.4.0",
    )(find_user)
    getAllUsers = deprecated(
        "getAllUsers has been renamed to get_all_users",
        includedoc="Replaced by :func:`get_all_users`",
        since="1.4.0",
    )(get_all_users)
    hasBeenCustomized = deprecated(
        "hasBeenCustomized has been renamed to has_been_customized",
        includedoc="Replaced by :func:`has_been_customized`",
        since="1.4.0",
    )(has_been_customized)


##~~ Exceptions


class UserAlreadyExists(Exception):
    def __init__(self, username):
        Exception.__init__(self, "User %s already exists" % username)


class UnknownUser(Exception):
    def __init__(self, username):
        Exception.__init__(self, "Unknown user: %s" % username)


class UnknownRole(Exception):
    def __init__(self, role):
        Exception.__init__(self, "Unknown role: %s" % role)


class CorruptUserStorage(Exception):
    pass


##~~ Refactoring helpers


class MethodReplacedByBooleanProperty:
    def __init__(self, name, message, getter):
        self._name = name
        self._message = message
        self._getter = getter

    @property
    def _attr(self):
        return self._getter()

    def __call__(self):
        from warnings import warn

        warn(DeprecationWarning(self._message.format(name=self._name)), stacklevel=2)
        return self._attr

    def __eq__(self, other):
        return self._attr == other

    def __ne__(self, other):
        return self._attr != other

    def __bool__(self):
        # Python 3
        return self._attr

    def __nonzero__(self):
        # Python 2
        return self._attr

    def __hash__(self):
        return hash(self._attr)

    def __repr__(self):
        return "MethodReplacedByProperty({}, {}, {})".format(
            self._name, self._message, self._getter
        )

    def __str__(self):
        return str(self._attr)


# TODO: Remove compatibility layer in OctoPrint 1.5.0
class FlaskLoginMethodReplacedByBooleanProperty(MethodReplacedByBooleanProperty):
    def __init__(self, name, getter):
        message = (
            "{name} is now a property in Flask-Login versions >= 0.3.0, which OctoPrint now uses. "
            + "Use {name} instead of {name}(). This compatibility layer will be removed in OctoPrint 1.5.0."
        )
        MethodReplacedByBooleanProperty.__init__(self, name, message, getter)


# TODO: Remove compatibility layer in OctoPrint 1.5.0
class OctoPrintUserMethodReplacedByBooleanProperty(MethodReplacedByBooleanProperty):
    def __init__(self, name, getter):
        message = (
            "{name} is now a property for consistency reasons with Flask-Login versions >= 0.3.0, which "
            + "OctoPrint now uses. Use {name} instead of {name}(). This compatibility layer will be removed "
            + "in OctoPrint 1.5.0."
        )
        MethodReplacedByBooleanProperty.__init__(self, name, message, getter)


##~~ User object


class User(UserMixin):
    def __init__(
        self,
        username,
        passwordHash,
        active,
        permissions=None,
        groups=None,
        apikey=None,
        settings=None,
    ):
        if permissions is None:
            permissions = []
        if groups is None:
            groups = []

        self._username = username
        self._passwordHash = passwordHash
        self._active = active
        self._permissions = permissions
        self._groups = groups
        self._apikey = apikey

        if settings is None:
            settings = {}

        self._settings = settings

    def as_dict(self):
        from octoprint.access.permissions import OctoPrintPermission

        return {
            "name": self._username,
            "active": bool(self.is_active),
            "permissions": list(map(lambda p: p.key, self._permissions)),
            "groups": list(map(lambda g: g.key, self._groups)),
            "needs": OctoPrintPermission.convert_needs_to_dict(self.needs),
            "apikey": self._apikey,
            "settings": self._settings,
            # TODO: deprecated, remove in 1.5.0
            "admin": self.has_permission(Permissions.ADMIN),
            "user": not self.is_anonymous,
            "roles": self._roles,
        }

    def check_password(self, passwordHash):
        return self._passwordHash == passwordHash

    def get_id(self):
        return self.get_name()

    def get_name(self):
        return self._username

    @property
    def is_anonymous(self):
        return FlaskLoginMethodReplacedByBooleanProperty("is_anonymous", lambda: False)

    @property
    def is_authenticated(self):
        return FlaskLoginMethodReplacedByBooleanProperty("is_authenticated", lambda: True)

    @property
    def is_active(self):
        return FlaskLoginMethodReplacedByBooleanProperty(
            "is_active", lambda: self._active
        )

    def get_all_settings(self):
        return self._settings

    def get_setting(self, key):
        if not isinstance(key, (tuple, list)):
            path = [key]
        else:
            path = key

        return self._get_setting(path)

    def set_setting(self, key, value):
        if not isinstance(key, (tuple, list)):
            path = [key]
        else:
            path = key
        return self._set_setting(path, value)

    def _get_setting(self, path):
        s = self._settings
        for p in path:
            if isinstance(s, dict) and p in s:
                s = s[p]
            else:
                return None
        return s

    def _set_setting(self, path, value):
        s = self._settings
        for p in path[:-1]:
            if p not in s:
                s[p] = {}

            if not isinstance(s[p], dict):
                s[p] = {}

            s = s[p]

        key = path[-1]
        s[key] = value
        return True

    def add_permissions_to_user(self, permissions):
        # Make sure the permissions variable is of type list
        if not isinstance(permissions, list):
            permissions = [permissions]

        assert all(map(lambda p: isinstance(p, OctoPrintPermission), permissions))

        dirty = False
        for permission in permissions:
            if permissions not in self._permissions:
                self._permissions.append(permission)
                dirty = True

        return dirty

    def remove_permissions_from_user(self, permissions):
        # Make sure the permissions variable is of type list
        if not isinstance(permissions, list):
            permissions = [permissions]

        assert all(map(lambda p: isinstance(p, OctoPrintPermission), permissions))

        dirty = False
        for permission in permissions:
            if permission in self._permissions:
                self._permissions.remove(permission)
                dirty = True

        return dirty

    def add_groups_to_user(self, groups):
        # Make sure the groups variable is of type list
        if not isinstance(groups, list):
            groups = [groups]

        assert all(map(lambda p: isinstance(p, Group), groups))

        dirty = False
        for group in groups:
            if group.is_toggleable() and group not in self._groups:
                self._groups.append(group)
                dirty = True

        return dirty

    def remove_groups_from_user(self, groups):
        # Make sure the groups variable is of type list
        if not isinstance(groups, list):
            groups = [groups]

        assert all(map(lambda p: isinstance(p, Group), groups))

        dirty = False
        for group in groups:
            if group.is_toggleable() and group in self._groups:
                self._groups.remove(group)
                dirty = True

        return dirty

    @property
    def permissions(self):
        if self._permissions is None:
            return []

        if Permissions.ADMIN in self._permissions:
            return Permissions.all()

        return list(filter(lambda p: p is not None, self._permissions))

    @property
    def groups(self):
        return list(self._groups)

    @property
    def effective_permissions(self):
        if self._permissions is None:
            return []
        return list(
            filter(lambda p: p is not None and self.has_permission(p), Permissions.all())
        )

    @property
    def needs(self):
        needs = set()

        for permission in self.permissions:
            if permission is not None:
                needs = needs.union(permission.needs)

        for group in self.groups:
            if group is not None:
                needs = needs.union(group.needs)

        return needs

    def has_permission(self, permission):
        return self.has_needs(*permission.needs)

    def has_needs(self, *needs):
        return set(needs).issubset(self.needs)

    def __repr__(self):
        return (
            "User(id=%s,name=%s,active=%r,user=True,admin=%r,permissions=%s,groups=%s)"
            % (
                self.get_id(),
                self.get_name(),
                bool(self.is_active),
                self.has_permission(Permissions.ADMIN),
                self._permissions,
                self._groups,
            )
        )

    # ~~ Deprecated methods & properties follow

    # TODO: Remove deprecated methods & properties in OctoPrint 1.5.0

    asDict = deprecated(
        "asDict has been renamed to as_dict",
        includedoc="Replaced by :func:`as_dict`",
        since="1.4.0",
    )(as_dict)

    @property
    @deprecated("is_user is deprecated, please use has_permission", since="1.4.0")
    def is_user(self):
        return OctoPrintUserMethodReplacedByBooleanProperty(
            "is_user", lambda: not self.is_anonymous
        )

    @property
    @deprecated("is_admin is deprecated, please use has_permission", since="1.4.0")
    def is_admin(self):
        return OctoPrintUserMethodReplacedByBooleanProperty(
            "is_admin", lambda: self.has_permission(Permissions.ADMIN)
        )

    @property
    @deprecated("roles is deprecated, please use has_permission", since="1.4.0")
    def roles(self):
        return self._roles

    @property
    def _roles(self):
        """Helper for the deprecated self.roles and serializing to yaml"""
        if self.has_permission(Permissions.ADMIN):
            return ["user", "admin"]
        elif not self.is_anonymous:
            return ["user"]
        else:
            return []


class AnonymousUser(AnonymousUserMixin, User):
    def __init__(self, groups):
        User.__init__(self, None, "", True, [], groups)

    @property
    def is_anonymous(self):
        return FlaskLoginMethodReplacedByBooleanProperty("is_anonymous", lambda: True)

    @property
    def is_authenticated(self):
        return FlaskLoginMethodReplacedByBooleanProperty(
            "is_authenticated", lambda: False
        )

    @property
    def is_active(self):
        return FlaskLoginMethodReplacedByBooleanProperty(
            "is_active", lambda: self._active
        )

    def check_password(self, passwordHash):
        return True

    def as_dict(self):
        from octoprint.access.permissions import OctoPrintPermission

        return {"needs": OctoPrintPermission.convert_needs_to_dict(self.needs)}

    def __repr__(self):
        return "AnonymousUser(groups=%s)" % self._groups


class SessionUser(wrapt.ObjectProxy):
    def __init__(self, user):
        wrapt.ObjectProxy.__init__(self, user)

        self._self_session = "".join("%02X" % z for z in bytes(uuid.uuid4().bytes))
        self._self_created = time.monotonic()
        self._self_touched = time.monotonic()

    @property
    def session(self):
        return self._self_session

    @property
    def created(self):
        return self._self_created

    @property
    def touched(self):
        return self._self_touched

    def touch(self):
        self._self_touched = time.monotonic()

    @deprecated(
        "SessionUser.get_session() has been deprecated, use SessionUser.session instead",
        since="1.3.5",
    )
    def get_session(self):
        return self.session

    def update_user(self, user):
        self.__wrapped__ = user

    def as_dict(self):
        result = self.__wrapped__.as_dict()
        result.update({"session": self.session})
        return result

    def __repr__(self):
        return "SessionUser({!r},session={},created={})".format(
            self.__wrapped__, self.session, self.created
        )


##~~ User object to use when global api key is used to access the API


class ApiUser(User):
    def __init__(self, groups):
        User.__init__(self, "_api", "", True, [], groups)
