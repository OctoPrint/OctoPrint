/*
 * Will get included into the login dialog, NOT into the regular OctoPrint
 * web application.
 */

$(function() {
    var overlayElement = $("#login-overlay");
    var errorElement = $("#login-error");
    var offlineElement = $("#login-offline");
    var buttonElement = $("#login-button");
    var reconnectElement = $("#login-reconnect");

    buttonElement.click(function() {
        var usernameElement = $("#login-user");
        var passwordElement = $("#login-password");
        var rememberElement = $("#login-remember");

        var username = usernameElement.val();
        var password = passwordElement.val();
        var remember = rememberElement.prop("checked");

        overlayElement.addClass("in");
        errorElement.removeClass("in");

        OctoPrint.browser.login(username, password, remember)
            .done(function() {
                location.reload();
            })
            .fail(function() {
                usernameElement.val("");
                passwordElement.val("");

                overlayElement.removeClass("in");
                errorElement.addClass("in");
            });

        return false;
    });

    var OctoPrint = window.OctoPrint;

    OctoPrint.options.baseurl = BASE_URL;

    OctoPrint.socket.onConnected = function() {
        buttonElement.prop("disabled", false);
        offlineElement.removeClass("in");
    };

    OctoPrint.socket.onDisconnected = function() {
        buttonElement.prop("disabled", true);
        offlineElement.addClass("in");
    };

    reconnectElement.click(function() {
        OctoPrint.socket.reconnect();
    });

    OctoPrint.socket.connect();
});
