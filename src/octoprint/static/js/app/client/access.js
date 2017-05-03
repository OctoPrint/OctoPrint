(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define("OctoPrintAccessClient", ["OctoPrintClient"], factory);
    } else {
        global.OctoPrintAccessClient = factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var PluginRegistry = function(access) {
        this.access = access;
        this.base = this.access.base;

        this.components = {};
    };

    var OctoPrintAccessClient = function(base) {
        this.base = base;

        this.components = {};
        this.pluginRegistry = new PluginRegistry(this);
    };

    OctoPrintAccessClient.registerComponent = function(name, component) {
        Object.defineProperty(OctoPrintAccessClient.prototype, name, {
            get: function() {
                if (this.components[name] !== undefined) {
                    return this.components[name];
                }

                var instance = new component(this);
                this.components[name] = instance;
                return instance;
           },
            enumerable: false,
            configurable: false
        });
    };

    OctoPrintClient.registerPluginComponent = function(name, component) {
        Object.defineProperty(PluginRegistry.prototype, name, {
            get: function() {
                if (this.components[name] !== undefined) {
                    return this.components[name];
                }

                var instance = new component(this.base);
                this.components[name] = instance;
                return instance;
            },
            enumerable: false,
            configurable: false
        });
    };

    OctoPrintClient.registerComponent("access", OctoPrintAccessClient);
    return OctoPrintAccessClient;
});
