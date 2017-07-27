ko.bindingHandlers.toggleContent = {
    init: function(element, valueAccessor) {
        var $elm = $(element),
            options = $.extend({
                class: null,
                container: null,
                parent: null,
                onComplete: function() {
                    $(document).trigger("slideCompleted");
                }
            }, valueAccessor());

        $elm.on("click", function(e) {
            e.preventDefault();
            if(options.class) {
                $elm.children('[class^="icon-"]').toggleClass(options.class);
                $elm.children('[class^="fa"]').toggleClass(options.class);
            }
            if(options.container) {
                if(options.parent) {
                    $elm.parents(options.parent).find(options.container).stop().slideToggle('fast', options.onComplete);
                } else {
                    $(options.container).stop().slideToggle('fast', options.onComplete);
                }
            }

        });
    }
};
