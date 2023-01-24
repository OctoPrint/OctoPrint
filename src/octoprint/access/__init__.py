import logging

ADMIN_GROUP = "admins"
USER_GROUP = "users"
GUEST_GROUP = "guests"
READONLY_GROUP = "readonly"


def auth_log(message):
    logging.getLogger("AUTH").info(message)


login_mechanisms = login_mechanism_lut = {
    "http": "credentials",
    "autologin": "autologin",
    "remember_me": "Remember Me cookie",
    "basic_auth": "Basic Authorization header",
    "remote_user": "Remote User header",
}
