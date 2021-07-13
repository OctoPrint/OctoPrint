ko.bindingHandlers.invisible = {
    init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
        var val = ko.utils.unwrapObservable(valueAccessor());
        ko.bindingHandlers.style.update(element, function () {
            return {visibility: val ? "hidden" : "visible"};
        });
    },
    update: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
        var val = ko.utils.unwrapObservable(valueAccessor());
        ko.bindingHandlers.style.update(element, function () {
            return {visibility: val ? "hidden" : "visible"};
        });
    }
};
