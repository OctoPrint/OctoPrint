// Maxheight
(function (factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        // CommonJS
        module.exports = factory(require('jquery'), require('pnotify'));
    } else if (typeof define === 'function' && define.amd) {
        // AMD. Register as a module.
        define('pnotify.confirm', ['jquery', 'pnotify'], factory);
    } else {
        // Browser globals
        factory(jQuery, PNotify);
    }
}(function($, PNotify){
    PNotify.prototype.options.maxheight = {
        // Maximum height of text area to enforce
        maxheight: false
    };

    var _position = PNotify.prototype.position;
    PNotify.prototype.position = function(){
        if (typeof this.options.maxheight.maxheight === "function") {
            setMaxHeight(this, this.options.maxheight);
        }
        _position.apply(this, arguments);
    };

    var setMaxHeight = function(notice, options) {
        if (!options.maxheight) return;

        var option = options.maxheight;
        if (typeof option === "function") {
            option = option();
        }

        var height;
        if (typeof option === "number") {
            // assuming pixels
            height = "" + option + "px";
        } else if (typeof option === "string") {
            // assuming css string
            height = option
        } else {
            // unknown, ignore
            return;
        }
        notice.text_container.css("max-height", height);
        notice.text_container.css("overflow-x", "hidden");
        notice.text_container.css("overflow-y", "auto");
    };

    PNotify.prototype.modules.maxheight = {
        init: setMaxHeight,
        update: setMaxHeight
    };
}));
