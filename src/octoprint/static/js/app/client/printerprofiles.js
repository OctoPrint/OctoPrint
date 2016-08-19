(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint", "jquery"], factory);
    } else {
        factory(window.OctoPrint, window.$);
    }
})(window || this, function(OctoPrint, $) {
    var url = "api/printerprofiles";

    var profileUrl = function(profile) {
        return url + "/" + profile;
    };

    OctoPrint.printerprofiles = {
        list: function (opts) {
            return OctoPrint.get(url, opts);
        },

        add: function (profile, additional, opts) {
            profile = profile || {};
            additional = additional || {};

            var data = $.extend({}, additional);
            data.profile = profile;

            return OctoPrint.postJson(url, data, opts);
        },

        get: function (id, opts) {
            return OctoPrint.get(profileUrl(id), opts);
        },

        update: function (id, profile, additional, opts) {
            profile = profile || {};
            additional = additional || {};

            var data = $.extend({}, additional);
            data.profile = profile;

            return OctoPrint.patchJson(profileUrl(id), data, opts);
        },

        delete: function (id, opts) {
            return OctoPrint.delete(profileUrl(id), opts);
        }
    }
});
