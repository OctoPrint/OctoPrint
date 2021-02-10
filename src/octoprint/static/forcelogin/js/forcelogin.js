/*
 * Will get included into the login dialog, NOT into the regular OctoPrint
 * web application.
 */

$(function () {
    var overlayElement = $("#login-overlay");
    var errorElement = $("#login-error");
    var offlineElement = $("#login-offline");
    var buttonElement = $("#login-button");
    var reconnectElement = $("#login-reconnect");

    buttonElement.click(function () {
        var usernameElement = $("#login-user");
        var passwordElement = $("#login-password");
        var rememberElement = $("#login-remember");

        var username = usernameElement.val();
        var password = passwordElement.val();
        var remember = rememberElement.prop("checked");

        overlayElement.addClass("in");
        errorElement.removeClass("in");

        OctoPrint.browser
            .login(username, password, remember)
            .done(function () {
                location.reload();
            })
            .fail(function () {
                usernameElement.val("");
                passwordElement.val("");

                overlayElement.removeClass("in");
                errorElement.addClass("in");
            });

        return false;
    });

    var OctoPrint = window.OctoPrint;

    OctoPrint.options.baseurl = BASE_URL;

    var offlineTimer = undefined;
    var clearOfflineTimer = function () {
        if (offlineTimer !== undefined) {
            window.clearTimeout(offlineTimer);
            offlineTimer = undefined;
        }
    };

    OctoPrint.socket.onConnected = function () {
        clearOfflineTimer();
        buttonElement.prop("disabled", false);
        offlineElement.removeClass("in");
    };

    OctoPrint.socket.onDisconnected = function () {
        clearOfflineTimer();
        offlineTimer = window.setTimeout(function () {
            buttonElement.prop("disabled", true);
            offlineElement.addClass("in");
        }, 1000);
    };

    reconnectElement.click(function () {
        OctoPrint.socket.reconnect();
    });

    OctoPrint.socket.connect();
});
