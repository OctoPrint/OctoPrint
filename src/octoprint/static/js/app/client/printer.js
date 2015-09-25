OctoPrint.printer = (function($, _) {
    var exports = {};

    var issuePrintheadCommand = function(command, payload, opts) {
        return OctoPrint.issueCommand("api/printer/printhead", command, payload, opts);
    };

    var issueToolCommand = function(command, payload, opts) {
        return OctoPrint.issueCommand("api/printer/tool", command, payload, opts);
    };

    var issueBedCommand = function(command, payload, opts) {
        return OctoPrint.issueCommand("api/printer/bed", command, payload, opts);
    };

    var issueSdCommand = function(command, payload, opts) {
        return OctoPrint.issueCommand("api/printer/sd", command, payload, opts);
    };

    exports.getFullState = function(data, opts) {
        data = data || {};

        var history = data.history || undefined;
        var limit = data.limit || undefined;
        var exclude = data.exclude || undefined;

        var url = "api/printer";
        if (history || exclude) {
            url += "?";
            if (history) {
                url += "history=true&";
                if (limit) {
                    url += "limit=" + limit + "&";
                }
            }

            if (exclude) {
                url += "exclude=" + exclude.join(",") + "&";
            }
        }

        return OctoPrint.get(url, opts);
    };

    exports.getToolState = function(data, opts) {
        data = data || {};

        var history = data.history || undefined;
        var limit = data.limit || undefined;

        var url = "api/printer/tool";
        if (history) {
            url += "?history=true";
            if (limit) {
                url += "&limit=" + limit;
            }
        }

        return OctoPrint.get(url, opts);
    };

    exports.getBedState = function(data, opts) {
        data = data || {};

        var history = data.history || undefined;
        var limit = data.limit || undefined;

        var url = "api/printer/bed";
        if (history) {
            url += "?history=true";
            if (limit) {
                url += "&limit=" + limit;
            }
        }

        return OctoPrint.get(url, opts);
    };

    exports.getSdState = function(opts) {
        return OctoPrint.get("api/printer/sd", opts);
    };

    exports.jog = function(data, opts) {
        data = data || {};

        var payload = {};
        if (data.x) payload.x = data.x;
        if (data.y) payload.y = data.y;
        if (data.z) payload.z = data.z;

        return issuePrintheadCommand("jog", payload, opts);
    };

    exports.home = function(axes, opts) {
        axes = axes || [];

        var payload = {
            axes: axes
        };

        return issuePrintheadCommand("home", payload, opts);
    };

    exports.setFeedrate = function(factor, opts) {
        factor = factor || 100;

        var payload = {
            factor: factor
        };

        return issuePrintheadCommand("feedrate", payload, opts);
    };

    exports.setToolTargetTemperatures = function(targets, opts) {
        targets = targets || {};

        var payload = {
            targets: targets
        };

        return issueToolCommand("target", payload, opts);
    };

    exports.setToolTemperatureOffsets = function(offsets, opts) {
        offsets = offsets || {};

        var payload = {
            offsets: offsets
        };

        return issueToolCommand("offset", payload, opts);
    };

    exports.selectTool = function(tool, opts) {
        tool = tool || undefined;

        var payload = {
            tool: tool
        };

        return issueToolCommand("select", payload, opts);
    };

    exports.extrude = function(amount, opts) {
        amount = amount || undefined;

        var payload = {
            amount: amount
        };

        return issueToolCommand("extrude", payload, opts);
    };

    exports.setFlowrate = function(factor, opts) {
        factor = factor || 100;

        var payload = {
            factor: factor
        };

        return issueToolCommand("flowrate", payload, opts);
    };

    exports.setBedTargetTemperature = function(temperature, opts) {
        temperature = temperature || 0;

        var payload = {
            target: temperature
        };

        return issueBedCommand("target", payload, opts);
    };

    exports.setBedTemperatureOffset = function(offset, opts) {
        offset = offset || 0;

        var payload = {
            offset: offset
        };

        return issueBedCommand("offset", payload, opts);
    };

    exports.initSd = function(opts) {
        return issueSdCommand("init", {}, opts);
    };

    exports.refreshSd = function(opts) {
        return issueSdCommand("refresh", {}, opts);
    };

    exports.releaseSd = function(opts) {
        return issueSdCommand("release", {}, opts);
    };

    return exports;
})($, _);
