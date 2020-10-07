ko.bindingHandlers.contextMenu = {
    init: function (
        element,
        valueAccessor,
        allBindingsAccessor,
        viewModel,
        bindingContext
    ) {
        var val = ko.utils.unwrapObservable(valueAccessor());

        $(element).contextMenu(val);
    },
    update: function (
        element,
        valueAccessor,
        allBindingsAccessor,
        viewModel,
        bindingContext
    ) {
        var val = ko.utils.unwrapObservable(valueAccessor());

        $(element).contextMenu(val);
    }
};
