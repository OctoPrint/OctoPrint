(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function (OctoPrintClient) {
    var url = "api/printer";
    var printheadUrl = url + "/printhead";
    var toolUrl = url + "/tool";
    var bedUrl = url + "/bed";
    var chamberUrl = url + "/chamber";
    var sdUrl = url + "/sd";
    var errorUrl = url + "/error";

    var OctoPrintPrinterClient = function (base) {
        this.base = base;
    };

    OctoPrintPrinterClient.prototype.issuePrintheadCommand = function (
        command,
        payload,
        opts
    ) {
        return this.base.issueCommand(printheadUrl, command, payload, opts);
    };

    OctoPrintPrinterClient.prototype.issueToolCommand = function (
        command,
        payload,
        opts
    ) {
        return this.base.issueCommand(toolUrl, command, payload, opts);
    };

    OctoPrintPrinterClient.prototype.issueBedCommand = function (command, payload, opts) {
        return this.base.issueCommand(bedUrl, command, payload, opts);
    };

    OctoPrintPrinterClient.prototype.issueChamberCommand = function (
        command,
        payload,
        opts
    ) {
        return this.base.issueCommand(chamberUrl, command, payload, opts);
    };

    OctoPrintPrinterClient.prototype.issueSdCommand = function (command, payload, opts) {
        return this.base.issueCommand(sdUrl, command, payload, opts);
    };

    OctoPrintPrinterClient.prototype.getFullState = function (flags, opts) {
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

        return this.base.get(getUrl, opts);
    };

    OctoPrintPrinterClient.prototype.getToolState = function (flags, opts) {
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

        return this.base.get(getUrl, opts);
    };

    OctoPrintPrinterClient.prototype.getBedState = function (flags, opts) {
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

        return this.base.get(getUrl, opts);
    };

    OctoPrintPrinterClient.prototype.getChamberState = function (flags, opts) {
        flags = flags || {};

        var history = flags.history || undefined;
        var limit = flags.limit || undefined;

        var getUrl = chamberUrl;
        if (history) {
            getUrl += "?history=true";
            if (limit) {
                getUrl += "&limit=" + limit;
            }
        }

        return this.base.get(getUrl, opts);
    };

    OctoPrintPrinterClient.prototype.getSdState = function (opts) {
        return this.base.get(sdUrl, opts);
    };

    OctoPrintPrinterClient.prototype.getErrorInfo = function (opts) {
        return this.base.get(errorUrl, opts);
    };

    OctoPrintPrinterClient.prototype.jog = function (params, opts) {
        params = params || {};

        var absolute = params.absolute || false;

        var payload = {absolute: absolute};
        if (params.x) payload.x = params.x;
        if (params.y) payload.y = params.y;
        if (params.z) payload.z = params.z;
        if (params.speed !== undefined) payload.speed = params.speed;

        return this.issuePrintheadCommand("jog", payload, opts);
    };

    OctoPrintPrinterClient.prototype.home = function (axes, opts) {
        axes = axes || [];

        var payload = {
            axes: axes
        };

        return this.issuePrintheadCommand("home", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setFeedrate = function (factor, opts) {
        factor = factor || 100;

        var payload = {
            factor: factor
        };

        return this.issuePrintheadCommand("feedrate", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setToolTargetTemperatures = function (
        targets,
        opts
    ) {
        targets = targets || {};

        var payload = {
            targets: targets
        };

        return this.issueToolCommand("target", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setToolTemperatureOffsets = function (
        offsets,
        opts
    ) {
        offsets = offsets || {};

        var payload = {
            offsets: offsets
        };

        return this.issueToolCommand("offset", payload, opts);
    };

    OctoPrintPrinterClient.prototype.selectTool = function (tool, opts) {
        tool = tool || undefined;

        var payload = {
            tool: tool
        };

        return this.issueToolCommand("select", payload, opts);
    };

    OctoPrintPrinterClient.prototype.extrude = function (amount, opts) {
        amount = amount || undefined;

        var payload = {
            amount: amount
        };

        return this.issueToolCommand("extrude", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setFlowrate = function (factor, opts) {
        factor = factor || 100;

        var payload = {
            factor: factor
        };

        return this.issueToolCommand("flowrate", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setBedTargetTemperature = function (target, opts) {
        target = target || 0;

        var payload = {
            target: target
        };

        return this.issueBedCommand("target", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setBedTemperatureOffset = function (offset, opts) {
        offset = offset || 0;

        var payload = {
            offset: offset
        };

        return this.issueBedCommand("offset", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setChamberTargetTemperature = function (
        target,
        opts
    ) {
        target = target || 0;

        var payload = {
            target: target
        };

        return this.issueChamberCommand("target", payload, opts);
    };

    OctoPrintPrinterClient.prototype.setChamberTemperatureOffset = function (
        offset,
        opts
    ) {
        offset = offset || 0;

        var payload = {
            offset: offset
        };

        return this.issueChamberCommand("offset", payload, opts);
    };

    OctoPrintPrinterClient.prototype.initSd = function (opts) {
        return this.issueSdCommand("init", {}, opts);
    };

    OctoPrintPrinterClient.prototype.refreshSd = function (opts) {
        return this.issueSdCommand("refresh", {}, opts);
    };

    OctoPrintPrinterClient.prototype.releaseSd = function (opts) {
        return this.issueSdCommand("release", {}, opts);
    };

    OctoPrintClient.registerComponent("printer", OctoPrintPrinterClient);
    return OctoPrintPrinterClient;
});
