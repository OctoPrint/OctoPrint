ko.bindingHandlers.popover = {
    init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
        var val = ko.utils.unwrapObservable(valueAccessor());

        var options = {
            title: val.title,
            animation: val.animation,
            placement: val.placement,
            trigger: val.trigger,
            delay: val.delay,
            content: val.content,
            html: val.html
        };
        $(element).popover(options);
    }
};
