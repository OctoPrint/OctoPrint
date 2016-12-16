ko.bindingHandlers.invisible = {
    init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        if (!valueAccessor()) return;
        ko.bindingHandlers.style.update(element, function() {
            return { visibility: 'hidden' };
        })
    }
};
