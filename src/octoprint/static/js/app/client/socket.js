OctoPrint.socket = (function($, _, SockJS) {
    var exports = {};

    exports.options = {
        timeouts: [0, 1, 1, 2, 3, 5, 8, 13, 20, 40, 100]
    };

    var normalClose = 1000;

    var socket = undefined;
    var reconnecting = false;
    var reconnectTrial = 0;

    var onOpen = function() {
        reconnecting = false;
        reconnectTrial = 0;
    };

    var onClose = function(e) {
        if (e.code == normalClose) {
            return;
        }

        if (exports.onReconnectAttempt(reconnectTrial)) {
            return;
        }

        if (reconnectTrial < exports.options.timeouts.length) {
            var timeout = exports.options.timeouts[reconnectTrial];
            setTimeout(exports.reconnect, timeout * 1000);
            reconnectTrial++;
        } else {
            exports.onReconnectFailed();
        }
    };

    var onMessage = function(msg) {
        for (var prop in msg.data) {
            if (!msg.data.hasOwnProperty(prop)) {
                continue;
            }

            var data = msg.data[prop];

            switch (prop) {
                case "connected": {
                    exports.onConnected(data);
                    break;
                }
                case "history": {
                    exports.onHistoryData(data);
                    break;
                }
                case "current": {
                    exports.onCurrentData(data);
                    break;
                }
                case "event": {
                    var event = data["type"];
                    var payload = data["payload"];
                    exports.onEvent(event, payload);
                    break;
                }
                case "plugin": {
                    exports.onPluginMessage(data.plugin, data.data);
                    break;
                }
                case "timelapse": {
                    exports.onTimelapseSettings(data);
                    break;
                }
                case "slicingProgress": {
                    exports.onSlicingProgress(data.slicer, data.model_path, data.machinecode_path, data.progress);
                    break;
                }
            }
        }
    };

    exports.connect = function(opts) {
        opts = opts || {};

        exports.disconnect();

        var url = OctoPrint.options.baseurl;
        if (!_.endsWith(url, "/")) {
            url += "/";
        }

        socket = new SockJS(url + "sockjs", undefined, opts);
        socket.onopen = onOpen;
        socket.onclose = onClose;
        socket.onmessage = onMessage;
    };

    exports.reconnect = function() {
        exports.disconnect();
        socket = undefined;
        exports.connect();
    };

    exports.disconnect = function() {
        if (socket != undefined) {
            socket.close();
        }
    };

    exports.onConnected = function(data) {};
    exports.onCurrentData = function(data) {};
    exports.onHistoryData = function(data) {};
    exports.onEvent = function(event, data) {};
    exports.onPluginMessage = function(plugin, message) {};
    exports.onTimelapseSettings = function(data) {};
    exports.onSlicingProgress = function(slicer, modelPath, machinecodePath, progress) {};
    exports.onReconnectAttempt = function(trial) {};
    exports.onReconnectFailed = function() {};

    return exports;
})($, _, SockJS);
