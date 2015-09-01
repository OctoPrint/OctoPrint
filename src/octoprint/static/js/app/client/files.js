OctoPrint.files = (function($, _) {
    var self = {};

    self.get = function(opts) {
        var url = "api/files";
        var origin = opts.origin || "";

        if (origin && _.contains(["local", "sdcard"], origin)) {
            url += origin + "/"
        }

        OctoPrint.get_json({
            url: url,
            success: opts.success,
            error: opts.error,
            complete: opts.complete
        })
    };

    return self;
})($, _);
