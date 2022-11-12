$(function () {
    //~~ OctoPrint client setup

    var OctoPrint = window.OctoPrint;
    OctoPrint.options.baseurl = BASE_URL;

    //~~ Lodash setup

    _.mixin({sprintf: sprintf, vsprintf: vsprintf});

    //~~ View Model

    function ReverseProxyTestViewModel() {
        var self = this;

        var url = OctoPrint.getParsedBaseUrl();
        var cookieSuffix = OctoPrint.getCookieSuffix();
        var protocol = url.protocol;
        var path = url.pathname || "/";

        if (path && path !== "/") {
            if (path.endsWith("/")) {
                path = path.substring(0, path.length - 1);
            }
        }

        self.serverProtocol = protocol.substring(0, protocol.length - 1);
        self.serverName = url.hostname;
        self.serverPort = url.port || (url.protocol === "https:" ? 443 : 80);
        self.serverPath = path;
        self.cookieSuffix = cookieSuffix;

        self.serverProtocolMatch = self.serverProtocol == SERVER_PROTOCOL;
        self.serverNameMatch = self.serverName == SERVER_NAME;
        self.serverPortMatch = self.serverPort == SERVER_PORT;
        self.serverPathMatch = self.serverPath == SERVER_PATH;
        self.cookieSuffixMatch = self.cookieSuffix == COOKIE_SUFFIX;
    }

    var viewModel = new ReverseProxyTestViewModel();

    ko.applyBindings(viewModel, document.getElementById("reverse_proxy_test"));
});
