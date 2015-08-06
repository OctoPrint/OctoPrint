$(function() {
    function FooterViewModel(parameters) {
        var self = this;

        self.appendEnvironmentInfo = function(data, event){

            // Build bug reporting URL
            var environmentInfo = {
                src : "ui",
                version : $(".version").text(),
                userAgent : navigator ? navigator.appVersion : "Unknown"
            }

            var target = event.target;
            var url = target.href + '?' + $.param(environmentInfo);

            // Redirect to the url
            window.location.href = url;
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        FooterViewModel,
        [],
        ".footer"
    ]);
});
