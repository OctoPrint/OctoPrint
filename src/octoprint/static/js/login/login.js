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
    var errorCredentialsElement = $("#login-error-credentials");
    var errorRateElement = $("#login-error-rate");
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
        errorCredentialsElement.removeClass("in");
        errorRateElement.removeClass("in");

        OctoPrint.browser
            .login(username, password, remember)
            .done(() => {
                ignoreDisconnect = true;
                window.location.href = REDIRECT_URL;
            })
            .fail((xhr) => {
                usernameElement.val(USER_ID);
                passwordElement.val("");

                if (USER_ID) {
                    passwordElement.focus();
                } else {
                    usernameElement.focus();
                }

                overlayElement.removeClass("in");
                if (xhr.status === 429) {
                    errorRateElement.addClass("in");
                } else {
                    errorCredentialsElement.addClass("in");
                }
            });

        return false;
    });

    OctoPrint.options.baseurl = BASE_URL;

    OctoPrint.socket.onConnected = () => {
        buttonElement.prop("disabled", false);
        offlineElement.removeClass("in");
    };

    OctoPrint.socket.onDisconnected = () => {
        if (ignoreDisconnect) return;
        buttonElement.prop("disabled", true);
        offlineElement.addClass("in");
    };

    reconnectElement.click(() => {
        OctoPrint.socket.reconnect();
    });

    OctoPrint.socket.connect();
    OctoPrint.loginui.startedUp = true;
});
