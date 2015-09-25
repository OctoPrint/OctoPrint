OctoPrint.socket = (function($, _, SockJS) {
    var exports = {};

    exports.options = {
        timeouts: [0, 1, 1, 2, 3, 5, 8, 13, 20, 40, 100]
    };

    var normalClose = 1000;

    var socket = undefined;
    var reconnecting = false;
    var reconnectTrial = 0;
    var registeredHandlers = {};

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

    return exports;
})($, _, SockJS);
