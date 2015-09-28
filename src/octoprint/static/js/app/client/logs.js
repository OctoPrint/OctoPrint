(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/logs";

    OctoPrint.logs = {
        list: function(opts) {
            return OctoPrint.get(url, opts);
        },

        delete: function(file, opts) {
            var fileUrl = url + "/" + file;
            return OctoPrint.delete(fileUrl, opts);
        },

        download: function(file, opts) {
            var fileUrl = url + "/" + file;
            return OctoPrint.download(fileUrl, opts);
        }
    }
});
