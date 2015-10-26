$(function() {
    function AboutViewModel(parameters) {
        var self = this;

        self.aboutDialog = undefined;

        self.show = function() {
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
            self.aboutDialog = $('#about_dialog');
        };
    }

    OCTOPRINT_VIEWMODELS.push([
        AboutViewModel,
        [],
        ["#about_dialog", "#footer_about"]
    ]);
});
