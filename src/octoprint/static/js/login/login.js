/*
 * Will get included into the login dialog, NOT into the regular OctoPrint
 * web application.
 */

$(function () {
    const OctoPrint = window.OctoPrint;

    OctoPrint.loginui = {
        startedUp: false
    };

    const loginForm = $("#login");
    const mfaForm = $("#mfa");
    const mfaErrorElement = $("#mfa-error");

    const overlayElement = $("#login-overlay");
    const errorCredentialsElement = $("#login-error-credentials");
    const errorCsrfElement = $("#login-error-csrf");
    const errorRateElement = $("#login-error-rate");
    const errorMfaElement = $("#login-error-mfa");
    const offlineElement = $("#login-offline");
    const buttonElement = $("#login-button");
    const reconnectElement = $("#login-reconnect");

    let ignoreDisconnect = false;

    const xhrErrorJson = function (xhr) {
        if (!xhr.responseText) return null;
        try {
            return JSON.parse(xhr.responseText);
        } catch (e) {
            return null;
        }
    };

    const hideErrors = () => {
        errorCredentialsElement.removeClass("in");
        errorCsrfElement.removeClass("in");
        errorRateElement.removeClass("in");
        errorMfaElement.removeClass("in");
        mfaErrorElement.removeClass("in");
    };

    const performLogin = (mfaCredentials) => {
        const usernameElement = $("#login-user");
        const passwordElement = $("#login-password");
        const rememberElement = $("#login-remember");

        const username = usernameElement.val();
        const password = passwordElement.val();
        const remember = rememberElement.prop("checked");

        overlayElement.addClass("in");
        hideErrors();

        const opts = {};
        if (mfaCredentials) {
            opts.additionalPayload = mfaCredentials;
        }

        OctoPrint.browser
            .login(username, password, remember, opts)
            .done(() => {
                hideErrors();
                ignoreDisconnect = true;
                window.location.href = REDIRECT_URL;
            })
            .fail((xhr) => {
                const response = xhrErrorJson(xhr);

                if (xhr.status === 403 && response && response.mfa) {
                    showMfa(response.mfa);
                } else if (xhr.status === 403 && response && response.mfa_error) {
                    mfaErrorElement.text(response.mfa_error);
                    mfaErrorElement.addClass("in");
                } else {
                    usernameElement.val(USER_ID);
                    passwordElement.val("");

                    showPasswordForm();

                    if (USER_ID) {
                        passwordElement.focus();
                    } else {
                        usernameElement.focus();
                    }

                    if (xhr.status === 429) {
                        errorRateElement.addClass("in");
                    } else if (mfaCredentials) {
                        errorMfaElement.addClass("in");
                    } else if (xhr.status === 400) {
                        errorCsrfElement.addClass("in");
                    } else {
                        errorCredentialsElement.addClass("in");
                    }
                }

                overlayElement.removeClass("in");
            });
    };

    const showPasswordForm = () => {
        loginForm.show();
        mfaForm.hide();
    };

    const showMfa = (options) => {
        const mfaOptions = $("#mfa-options", mfaForm);
        mfaOptions.empty();

        _.each(options, (mfa) => {
            const formTemplate = $(`#mfa_login_${mfa}`);
            const title = formTemplate.data("title");
            const form = formTemplate.html();

            const container = $(`<div class="accordion-group"></div>`);
            const heading = $(
                `<div class="accordion-heading"><a role="heading" aria-level="2" aria-label="{{ title|edq }}" class="accordion-toggle" data-toggle="collapse" data-parent="#mfa-options" href="#mfa-form-${mfa}">${title}</a></div>`
            );
            const body = $(
                `<div class="accordion-body collapse in" id="mfa-form-${mfa}">${form}</div>`
            );
            container.append(heading).append(body);

            mfaOptions.append(container);

            $('button[type="submit"', container).click((e) => {
                e.preventDefault();
                const additional = {};
                _.each(["input", "select", "textarea"], (tag) => {
                    $(`${tag}[data-mfa]`, container).each((index, element) => {
                        const jqueryElement = $(element);
                        const input = jqueryElement.data("mfa");
                        additional[`mfa-${mfa}-${input}`] = jqueryElement.val();
                    });
                });
                performLogin(additional);
            });
        });

        mfaForm.show();
        mfaForm.find("input,textarea.select").filter(":visible:first").focus();
        loginForm.hide();
    };

    buttonElement.click(() => {
        performLogin();
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
