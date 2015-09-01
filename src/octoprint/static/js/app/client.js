var OctoPrint = (function($, _, SockJS) {
    var self = {
        options: {
            socketReconnectTimeouts: [0, 1, 1, 2, 3, 5, 8, 13, 20, 40, 100],
            socketDebug: false,
            socketNormalClose: 1000
        }
    };

    var _socket = undefined;
    var _socketAddress = undefined;
    var _socketReconnecting = false;
    var _socketReconnectTrial = 0;
    var _socketIgnoreReconnects = 1;

    function callCallback(callback, arguments) {
        if (!_.isFunction(self.options[callback])) {
            throw Error("No such callback: " + callback);
        }

        self.options[callback].bind(arguments);
    }

    function connect(socketAddress) {
        var address = socketAddress || _socketAddress;
        if (address == undefined) {
            return;
        }

        var socketOptions = {
            debug: options.socketDebug || false
        };

        if (_socket != undefined) {
            self._socket.close();
            delete self._socket;
        }

        _socketAddress = address;
        _socket = new SockJS(address, undefined, socketOptions);
        _socket.onopen = onSocketOpen;
        _socket.onclose = onSocketClose;
        _socket.onmessage = onSocketMessage;
    }

    function onSocketOpen() {
        _socketReconnecting = false;
        _socketReconnectTrial = 0;
    }

    function onSocketClose(error) {
        if (error.code == options.socketNormalClose) {
            return;
        }

        if (_socketReconnectTrial >= _socketIgnoreReconnects) {
            if (options.onAttemptingReconnect) {
                options.onAttemptingReconnect(_socketReconnectTrial);
            }
        }

        if (_socketReconnectTrial < options.socketReconnectTimeouts.length) {
            var timeout = options.socketReconnectTimeouts[_socketReconnectTrial];
            log.info("Reconnect trial #" + self._autoReconnectTrial + ", waiting " + timeout + "s");
            setTimeout(connect, timeout * 1000);
            _socketReconnectTrial++;
        } else {
            if (options.onReconnectFailed) {
                options.onReconnectFailed();
            }
        }
    }

    function onSocketMessage(data) {
    }

    return self;

}(jQuery, _, SockJS));
