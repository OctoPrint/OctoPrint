$(function() {
    function AboutViewModel(parameters) {
        var self = this;

        self.aboutDialog = undefined;
        self.aboutContent = undefined;
        self.aboutTabs = undefined;

        self.show = function() {
            $("a:first", self.aboutTabs).tab("show");
            self.aboutContent.scrollTop(0);
            self.aboutDialog.modal({
                minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });
            return false;
        };

        self.hide = function() {
            self.aboutDialog.modal("hide");
        };

        self.onStartup = function() {
            self.aboutDialog = $("#about_dialog");
            self.aboutTabs = $("#about_dialog_tabs");
            self.aboutContent = $("#about_dialog_content");

            $('a[data-toggle="tab"]', self.aboutTabs).on("show", function() {
                self.aboutContent.scrollTop(0);
            });
        };

        self.showTab = function(tab) {
            $("a[href=#" + tab + "]", self.aboutTabs).tab("show");
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AboutViewModel,
        elements: ["#about_dialog", "#footer_about"]
    });
});
