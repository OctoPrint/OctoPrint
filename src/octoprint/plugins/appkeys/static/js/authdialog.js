/*
 * Will get included into the auth dialog, NOT into the regular OctoPrint
 * web application.
 */

$(function () {
    var OctoPrint = window.OctoPrint;

    OctoPrint.authui = {
        startedUp: false
    };

    var offlineElement = $("#auth-offline");
    var grantButtonElement = $("#auth-grant");
    var rejectButtonElement = $("#auth-reject");

    var choiceElement = $("#auth-choice");
    var doneElement = $("#auth-done");
    var errorElement = $("#auth-error");

    var showDone = function () {
        choiceElement.hide();
        doneElement.show();
    };
    var showError = function () {
        choiceElement.hide();
        errorElement.show();
    };
    var showOffline = function () {
        choiceElement.hide();
        offlineElement.show();
    };

    grantButtonElement.click(function () {
        errorElement.removeClass("in");

        OctoPrint.plugins.appkeys
            .decide(USER_TOKEN, true)
            .done(function () {
                if (REDIRECT_URL) {
                    window.location.href = REDIRECT_URL;
                } else {
                    showDone();
                }
            })
            .fail(showError);

        return false;
    });
    rejectButtonElement.click(function () {
        OctoPrint.plugins.appkeys
            .decide(USER_TOKEN, false)
            .done(function () {
                if (REDIRECT_URL) {
                    window.location.href = REDIRECT_URL;
                } else {
                    showDone();
                }
            })
            .fail(showError);

        return false;
    });

    OctoPrint.options.baseurl = BASE_URL;

    OctoPrint.socket.onConnected = function () {
        OctoPrint.browser.passiveLogin().done(function (login) {
            OctoPrint.socket.sendAuth(login.name, login.session);
            OctoPrint.authui.startedUp = true;
        });
    };

    OctoPrint.socket.onDisconnected = function () {
        showOffline();
    };

    OctoPrint.socket.onMessage("plugin", function (event) {
        if (event.data.plugin !== "appkeys") return;

        var type = event.data.data.type;
        if (type !== "end_request") return;

        var token = event.data.data.user_token;
        if (token !== USER_TOKEN) return;

        showDone();
    });

    OctoPrint.socket.connect();
});
