import logging

ADMIN_GROUP = "admins"
USER_GROUP = "users"
GUEST_GROUP = "guests"
READONLY_GROUP = "readonly"


def auth_log(message):
    logging.getLogger("AUTH").info(message)
