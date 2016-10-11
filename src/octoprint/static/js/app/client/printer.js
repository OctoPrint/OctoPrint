(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/printer";
    var printheadUrl = url + "/printhead";
    var toolUrl = url + "/tool";
    var bedUrl = url + "/bed";
    var sdUrl = url + "/sd";

    var issuePrintheadCommand = function (command, payload, opts) {
        return OctoPrint.issueCommand(printheadUrl, command, payload, opts);
    };

    var issueToolCommand = function (command, payload, opts) {
        return OctoPrint.issueCommand(toolUrl, command, payload, opts);
    };

    var issueBedCommand = function (command, payload, opts) {
        return OctoPrint.issueCommand(bedUrl, command, payload, opts);
    };

    var issueSdCommand = function (command, payload, opts) {
        return OctoPrint.issueCommand(sdUrl, command, payload, opts);
    };

    OctoPrint.printer = {
        getFullState: function (flags, opts) {
            flags = flags || {};

            var history = flags.history || undefined;
            var limit = flags.limit || undefined;
            var exclude = flags.exclude || undefined;

            var getUrl = url;
            if (history || exclude) {
                getUrl += "?";
                if (history) {
                    getUrl += "history=true&";
                    if (limit) {
                        getUrl += "limit=" + limit + "&";
                    }
                }

                if (exclude) {
                    getUrl += "exclude=" + exclude.join(",") + "&";
                }
            }

            return OctoPrint.get(getUrl, opts);
        },

        getToolState: function (flags, opts) {
            flags = flags || {};

            var history = flags.history || undefined;
            var limit = flags.limit || undefined;

            var getUrl = toolUrl;
            if (history) {
                getUrl += "?history=true";
                if (limit) {
                    getUrl += "&limit=" + limit;
                }
            }

            return OctoPrint.get(getUrl, opts);
        },

        getBedState: function (flags, opts) {
            flags = flags || {};

            var history = flags.history || undefined;
            var limit = flags.limit || undefined;

            var getUrl = bedUrl;
            if (history) {
                getUrl += "?history=true";
                if (limit) {
                    getUrl += "&limit=" + limit;
                }
            }

            return OctoPrint.get(getUrl, opts);
        },

        getSdState: function (opts) {
            return OctoPrint.get(sdUrl, opts);
        },

        jog: function (params, opts) {
            params = params || {};

            var absolute = params.absolute || false;

            var payload = {absolute: absolute};
            if (params.x) payload.x = params.x;
            if (params.y) payload.y = params.y;
            if (params.z) payload.z = params.z;
            if (params.speed !== undefined) payload.speed = params.speed;

            return issuePrintheadCommand("jog", payload, opts);
        },

        home: function (axes, opts) {
            axes = axes || [];

            var payload = {
                axes: axes
            };

            return issuePrintheadCommand("home", payload, opts);
        },

        setFeedrate: function (factor, opts) {
            factor = factor || 100;

            var payload = {
                factor: factor
            };

            return issuePrintheadCommand("feedrate", payload, opts);
        },

        setToolTargetTemperatures: function (targets, opts) {
            targets = targets || {};

            var payload = {
                targets: targets
            };

            return issueToolCommand("target", payload, opts);
        },

        setToolTemperatureOffsets: function (offsets, opts) {
            offsets = offsets || {};

            var payload = {
                offsets: offsets
            };

            return issueToolCommand("offset", payload, opts);
        },

        selectTool: function (tool, opts) {
            tool = tool || undefined;

            var payload = {
                tool: tool
            };

            return issueToolCommand("select", payload, opts);
        },

        extrude: function (amount, opts) {
            amount = amount || undefined;

            var payload = {
                amount: amount
            };

            return issueToolCommand("extrude", payload, opts);
        },

        setFlowrate: function (factor, opts) {
            factor = factor || 100;

            var payload = {
                factor: factor
            };

            return issueToolCommand("flowrate", payload, opts);
        },

        setBedTargetTemperature: function (target, opts) {
            target = target || 0;

            var payload = {
                target: target
            };

            return issueBedCommand("target", payload, opts);
        },

        setBedTemperatureOffset: function (offset, opts) {
            offset = offset || 0;

            var payload = {
                offset: offset
            };

            return issueBedCommand("offset", payload, opts);
        },

        initSd: function (opts) {
            return issueSdCommand("init", {}, opts);
        },

        refreshSd: function (opts) {
            return issueSdCommand("refresh", {}, opts);
        },

        releaseSd: function (opts) {
            return issueSdCommand("release", {}, opts);
        }
    }
});
