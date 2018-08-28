(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintAppAuthClient = function(base) {
        this.base = base;
    };

    OctoPrintAppAuthClient.prototype.getKeys = function(opts) {
        return this.base.simpleApiGet("appauth", opts);
    };

    OctoPrintAppAuthClient.prototype.generateKey = function(app, opts) {
        return this.base.simpleApiCommand("appauth", "generate", {"app": app}, opts);
    };

    OctoPrintAppAuthClient.prototype.revokeKey = function(key, opts) {
        return this.base.simpleApiCommand("appauth", "revoke", {"key": key}, opts);
    };

    OctoPrintAppAuthClient.prototype.decide = function(token, decision, opts) {
        return this.base.postJson(this.base.getBlueprintUrl("appauth") + "decision/" + token, {decision: !!decision}, opts);
    };

    OctoPrintAppAuthClient.prototype.request = function(app, opts) {
        return this.requestForUser(app, undefined, opts);
    };

    OctoPrintAppAuthClient.prototype.requestForUser = function(app, user, opts) {
        return this.base.postJson(this.base.getBlueprintUrl("appauth") + "request", {app: app, user: user}, opts);
    };

    OctoPrintAppAuthClient.prototype.checkDecision = function(token, opts) {
        return this.base.get(this.base.getBlueprintUrl("appauth") + "request/" + token, opts);
    };

    OctoPrintAppAuthClient.prototype.authenticate = function(app, user) {
        var deferred = $.Deferred();
        var client = this;

        client.requestForUser(app, user)
            .done(function(response) {
                var token = response.app_token;
                if (!token) {
                    // no token received, something went wrong
                    deferred.reject();
                    return;
                }

                var interval = 1000;
                var poll = function() {
                    client.checkDecision(token)
                        .done(function(response) {
                            if (response.api_key) {
                                // got a decision, resolve the promise
                                deferred.resolve(response.api_key);
                            } else {
                                // no decision yet, poll a bit more
                                deferred.notify();
                                window.setTimeout(poll, interval);
                            }
                        })
                        .fail(function() {
                            // something went wrong
                            deferred.reject();
                        });
                };
                window.setTimeout(poll, interval);
            })
            .fail(function() {
                // something went wrong
                deferred.reject();
            });

        return deferred.promise();
    };

    OctoPrintClient.registerPluginComponent("appauth", OctoPrintAppAuthClient);
    return OctoPrintAppAuthClient;
});
