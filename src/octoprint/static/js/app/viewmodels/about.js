$(function () {
    function AboutViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.aboutDialog = undefined;
        self.aboutContent = undefined;
        self.aboutTabs = undefined;

        self.systeminfo = ko.observableArray();

        self.devmode = getQueryParameterByName("devmode") !== null;

        self.getSystemInfo = function () {
            if (!self.loginState.hasPermission(self.access.permissions.SYSTEM)) return;
            return OctoPrint.system.getInfo().done(self.fromSystemInfo);
        };

        self.fromSystemInfo = function (r) {
            var systeminfo = [];
            _.forOwn(r.systeminfo, function (value, key) {
                systeminfo.push({key: key, value: value});
            });
            self.systeminfo(systeminfo);
        };

        self.copySystemInfo = function () {
            var text = "";
            _.each(self.systeminfo(), function (entry) {
                text += entry.key + ": " + entry.value + "\r\n";
            });
            copyToClipboard(text);
        };

        self.show = function (tab) {
            if (tab) {
                $('a[href="#' + tab + '"]', self.aboutTabs).tab("show");
            } else {
                $("a:first", self.aboutTabs).tab("show");
            }
            self.aboutContent.scrollTop(0);

            const maxHeight = $.fn.modal.defaults.maxHeight() - 80 - 60;
            self.aboutDialog
                .modal({
                    minHeight: function () {
                        return Math.max(maxHeight, 250);
                    },
                    maxHeight: maxHeight
                })
                .css({
                    "margin-left": function () {
                        return -($(this).width() / 2);
                    }
                });
            self.getSystemInfo();
            return false;
        };

        self.hide = function () {
            self.aboutDialog.modal("hide");
        };

        self.onStartup = function () {
            self.aboutDialog = $("#about_dialog");
            self.aboutTabs = $("#about_dialog_tabs");
            self.aboutContent = $("#about_dialog_content");

            $('a[data-toggle="tab"]', self.aboutTabs).on("show", function () {
                self.aboutContent.scrollTop(0);
            });
        };

        self.onAllBound = function (allViewModels) {
            self.aboutDialog.on("show", function () {
                callViewModels(allViewModels, "onAboutShown");
            });
            self.aboutDialog.on("hidden", function () {
                callViewModels(allViewModels, "onAboutHidden");
            });
        };

        self.showTab = function (tab) {
            $('a[href="#' + tab + '"]', self.aboutTabs).tab("show");
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AboutViewModel,
        elements: [
            "#about_dialog",
            "#footer_about",
            "#footer_achievements",
            "#footer_systeminfo"
        ],
        dependencies: ["loginStateViewModel", "accessViewModel"]
    });
});
