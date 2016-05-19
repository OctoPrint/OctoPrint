(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery", "lodash", "sockjs"], factory);
    } else {
        factory(window.OctoPrint, window.$, window._, window.SockJS);
    }
})(window || this, function(OctoPrint, $, _, SockJS) {
    var exports = {};

    exports.options = {
        timeouts: [0, 1, 1, 2, 3, 5, 8, 13, 20, 40, 100],
        rateSlidingWindowSize: 20
    };

    var normalClose = 1000;

    var socket = undefined;
    var reconnecting = false;
    var reconnectTrial = 0;
    var registeredHandlers = {};

    var rateThrottleFactor = 1;
    var rateBase = 500;
    var rateLastMeasurements = [];

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
        _.each(msg.data, function(data, key) {
            propagateMessage(key, data);
        });
    };

    var propagateMessage = function(event, data) {
        if (!registeredHandlers.hasOwnProperty(event)) {
            return;
        }

        var start = new Date().getTime();

        var eventObj = {event: event, data: data};

        var catchAllHandlers = registeredHandlers["*"];
        if (catchAllHandlers && catchAllHandlers.length) {
            _.each(catchAllHandlers, function(handler) {
                handler({event: eventObj})
            });
        }

        var handlers = registeredHandlers[event];
        if (handlers && handlers.length) {
            _.each(handlers, function(handler) {
                handler(eventObj);
            });
        }

        var end = new Date().getTime();
        analyzeTiming(end - start);
    };

    var analyzeTiming = function(measurement) {
        while (rateLastMeasurements.length >= exports.options.rateSlidingWindowSize) {
            rateLastMeasurements.shift();
        }
        rateLastMeasurements.push(measurement);

        var processingLimit = rateThrottleFactor * rateBase;
        if (measurement > processingLimit) {
            exports.onRateTooHigh(measurement, processingLimit);
        } else if (rateThrottleFactor > 1) {
            var maxProcessingTime = Math.max.apply(null, rateLastMeasurements);
            var lowerProcessingLimit = (rateThrottleFactor - 1) * rateBase;
            if (maxProcessingTime < lowerProcessingLimit) {
                exports.onRateTooLow(maxProcessingTime, lowerProcessingLimit);
            }
        }
    };

    var increaseRate = function() {
        if (rateThrottleFactor <= 1) {
            rateThrottleFactor = 1;
            return;
        }
        rateThrottleFactor--;
        sendThrottleFactor();
    };

    var decreaseRate = function() {
        rateThrottleFactor++;
        sendThrottleFactor();
    };

    var sendThrottleFactor = function() {
        sendMessage("throttle", rateThrottleFactor);
    };

    var sendMessage = function(type, payload) {
        var data = {};
        data[type] = payload;
        socket.send(JSON.stringify(data));
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

    exports.onMessage = function(message, handler) {
        if (!registeredHandlers.hasOwnProperty(message)) {
            registeredHandlers[message] = [];
        }
        registeredHandlers[message].push(handler);
        return exports;
    };

    exports.onReconnectAttempt = function(trial) {};
    exports.onReconnectFailed = function() {};

    exports.onRateTooLow = function(measured, minimum) {
        increaseRate();
    };
    exports.onRateTooHigh = function(measured, maximum) {
        decreaseRate();
    };

    exports.increaseRate = increaseRate;
    exports.decreaseRate = decreaseRate;
    exports.sendMessage = sendMessage;

    OctoPrint.socket = exports;
});
