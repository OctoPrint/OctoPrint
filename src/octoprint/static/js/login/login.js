/*
 * Will get included into the login dialog, NOT into the regular OctoPrint
 * web application.
 */

$(function () {
    var OctoPrint = window.OctoPrint;

    OctoPrint.loginui = {
        startedUp: false
    };

    var overlayElement = $("#login-overlay");
    var errorElement = $("#login-error");
    var offlineElement = $("#login-offline");
    var buttonElement = $("#login-button");
    var reconnectElement = $("#login-reconnect");

    var ignoreDisconnect = false;

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
                ignoreDisconnect = true;
                window.location.href = REDIRECT_URL;
            })
            .fail(function () {
                usernameElement.val(USER_ID);
                passwordElement.val("");

                if (USER_ID) {
                    passwordElement.focus();
                } else {
                    usernameElement.focus();
                }

                overlayElement.removeClass("in");
                errorElement.addClass("in");
            });

        return false;
    });

    OctoPrint.options.baseurl = BASE_URL;

    OctoPrint.socket.onConnected = function () {
        buttonElement.prop("disabled", false);
        offlineElement.removeClass("in");
    };

    OctoPrint.socket.onDisconnected = function () {
        if (ignoreDisconnect) return;
        buttonElement.prop("disabled", true);
        offlineElement.addClass("in");
    };

    reconnectElement.click(function () {
        OctoPrint.socket.reconnect();
    });

    OctoPrint.socket.connect();
    OctoPrint.loginui.startedUp = true;
});
