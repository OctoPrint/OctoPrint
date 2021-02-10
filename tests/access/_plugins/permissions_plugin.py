def plugin_permissions(components):
    return [
        {
            "name": "fancy permission",
            "description": "My Fancy new Permission",
            "roles": ["fancy"],
        },
        {
            "name": "fancy permission with two roles",
            "description": "My Fancy new Permission with two roles",
            "roles": ["fancy1", "fancy2"],
        },
    ]


__plugin_name__ = "Permissions Plugin"
__plugin_description__ = "Test permissions plugin"
__plugin_hooks__ = {
    "octoprint.access.permissions": plugin_permissions,
}
