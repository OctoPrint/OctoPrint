ko.bindingHandlers.popover = {
    keys: ["title", "animation", "placement", "trigger", "delay", "content", "html"],

    init: function (
        element,
        valueAccessor,
        allBindingsAccessor,
        viewModel,
        bindingContext
    ) {
        var val = ko.utils.unwrapObservable(valueAccessor());

        var keys = ko.bindingHandlers.popover.keys;
        var options = {};
        _.each(keys, function (key) {
            options[key] = ko.utils.unwrapObservable(val[key]);
        });

        $(element).popover(options);
    },

    update: function (
        element,
        valueAccessor,
        allBindingsAccessor,
        viewModel,
        bindingContext
    ) {
        var val = ko.utils.unwrapObservable(valueAccessor());

        var keys = ko.bindingHandlers.popover.keys;
        var value;
        _.each(keys, function (key) {
            value = ko.utils.unwrapObservable(val[key]);
            $(element).data("popover").options[key] = value;
        });
    }
};
