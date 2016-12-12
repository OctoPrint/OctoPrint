$(function() {
    function PermissionsViewModel() {
        var self = this;

        self.permissionsList = ko.observableArray([]);

        self.need = function(method, value) { return {method: method, value: value}; };
        self.roleNeed = function(value) { return self.need("role", value); };

        self.ADMIN = self.roleNeed("admin");
        self.USER = self.roleNeed("user");

        self.STATUS = self.roleNeed("status");
        self.CONNECTION = self.roleNeed("connection");
        self.WEBCAM = self.roleNeed("webcam");
        self.SYSTEM = self.roleNeed("system");
        self.UPLOAD = self.roleNeed("upload");
        self.DOWNLOAD = self.roleNeed("download");
        self.DELETE = self.roleNeed("delete");
        self.SELECT = self.roleNeed("select");
        self.PRINT = self.roleNeed("printing");
        self.TERMINAL = self.roleNeed("terminal");
        self.CONTROL = self.roleNeed("control");
        self.SLICE = self.roleNeed("slice");
        self.TIMELAPSE = self.roleNeed("timelapse");
        self.TIMELAPSE_ADMIN = self.roleNeed("timelapse_admin");
        self.SETTINGS = self.roleNeed("settings");
        self.LOGS = self.roleNeed("logs");

        self.requestData = function() {
            if (!CONFIG_ACCESS_CONTROL) return;

            OctoPrint.permissions.list().done(function(response) {
                self.permissionsList(response.permissions);
            });
        };

        self.onAllBound = function(allViewModels) {
            self.allViewModels = allViewModels;
        };

        self.onStartupComplete = self.onServerConnect = self.onServerReconnect = function() {
            if (self.allViewModels == undefined) return;
            self.requestData();
        };

        self.hasPermissions = function(listtocheck, permissionsList) {
            if (permissionsList === undefined || listtocheck === undefined || listtocheck.length == 0)
                return false;

            has_all_permissions = self.hasPermission(listtocheck[0], permissionsList);
            for (var i = 1; i < listtocheck.length && has_all_permissions; i++) {
                has_all_permissions &= self.hasPermission(listtocheck[i], permissionsList);
            }
            return has_all_permissions;
        };
        self.hasPermission = function(permission, permissions) {
            if (permissions === undefined || permission === undefined)
                return false;

            for (var i = 0; i < permissions.length; i++)
            {
                var p = permissions[i];
                if (p != undefined && (p.name === "Admin" ||
                   (p.needs.hasOwnProperty(permission.method) && p.needs[permission.method].indexOf(permission.value) != -1)))
                    return true;
            }

            return false;
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        PermissionsViewModel,
        [],
        []
    ]);
});
