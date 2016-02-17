(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/languages";

    OctoPrint.languages = {
        list: function(opts) {
            return OctoPrint.get(url, opts);
        },
        upload: function(file) {
            return OctoPrint.upload(url, file);
        },
        delete: function(locale, pack, opts) {
            var packUrl = url + "/" + locale + "/" + pack;
            return OctoPrint.delete(packUrl, opts);
        }
    };
});
