(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var OctoPrintAppKeysClient = function (base) {
        this.base = base;
    };

    OctoPrintAppKeysClient.prototype.getKeys = function (opts) {
        return this.base.simpleApiGet("appkeys", opts);
    };

    OctoPrintAppKeysClient.prototype.getAllKeys = function (opts) {
        return this.base.get(this.base.getSimpleApiUrl("appkeys") + "?all=true", opts);
    };

    OctoPrintAppKeysClient.prototype.getKey = function (app, user, opts) {
        return this.base.get(
            this.base.getSimpleApiUrl("appkeys") +
                "?app=" +
                encodeURIComponent(app) +
                (user ? "&user=" + encodeURIComponent(user) : ""),
            opts
        );
    };

    OctoPrintAppKeysClient.prototype.generateKey = function (app, opts) {
        return this.base.simpleApiCommand("appkeys", "generate", {app: app}, opts);
    };

    OctoPrintAppKeysClient.prototype.generateKeyForUser = function (user, app, opts) {
        return this.base.simpleApiCommand(
            "appkeys",
            "generate",
            {app: app, user: user},
            opts
        );
    };

    OctoPrintAppKeysClient.prototype.revokeKey = function (key, opts) {
        console.log(
            "revokeKey should be considered deprecated, use revokeKeyForApp instead"
        );
        return this.base.simpleApiCommand("appkeys", "revoke", {key: key}, opts);
    };

    OctoPrintAppKeysClient.prototype.revokeKeyForApp = function (app, user, opts) {
        const params = {app: app};
        if (user) {
            params.user = user;
        }
        return this.base.simpleApiCommand("appkeys", "revoke", params, opts);
    };

    OctoPrintAppKeysClient.prototype.decide = function (token, decision, opts) {
        return this.base.postJson(
            this.base.getBlueprintUrl("appkeys") + "decision/" + token,
            {decision: !!decision},
            opts
        );
    };

    OctoPrintAppKeysClient.prototype.probe = function (opts) {
        return this.base.get(this.base.getBlueprintUrl("appkeys") + "probe", opts);
    };

    OctoPrintAppKeysClient.prototype.request = function (app, opts) {
        return this.requestForUser(app, undefined, opts);
    };

    OctoPrintAppKeysClient.prototype.requestForUser = function (app, user, opts) {
        return this.base.postJson(
            this.base.getBlueprintUrl("appkeys") + "request",
            {app: app, user: user},
            opts
        );
    };

    OctoPrintAppKeysClient.prototype.checkDecision = function (token, opts) {
        return this.base.get(
            this.base.getBlueprintUrl("appkeys") + "request/" + token,
            opts
        );
    };

    OctoPrintAppKeysClient.prototype.authenticate = function (app, user) {
        var deferred = $.Deferred();
        var client = this;

        client
            .probe()
            .done(function () {
                client
                    .requestForUser(app, user)
                    .done(function (response) {
                        var token = response.app_token;
                        if (!token) {
                            // no token received, something went wrong
                            deferred.reject();
                            return;
                        }

                        var interval = 1000;
                        var poll = function () {
                            client
                                .checkDecision(token)
                                .done(function (response) {
                                    if (response.api_key) {
                                        // got a decision, resolve the promise
                                        deferred.resolve(response.api_key);
                                    } else {
                                        // no decision yet, poll a bit more
                                        deferred.notify();
                                        window.setTimeout(poll, interval);
                                    }
                                })
                                .fail(function () {
                                    // something went wrong
                                    deferred.reject();
                                });
                        };
                        window.setTimeout(poll, interval);
                    })
                    .fail(function () {
                        // something went wrong
                        deferred.reject();
                    });
            })
            .fail(function () {
                // workflow unsupported
                deferred.reject();
            });

        return deferred.promise();
    };

    OctoPrintClient.registerPluginComponent("appkeys", OctoPrintAppKeysClient);
    return OctoPrintAppKeysClient;
});
