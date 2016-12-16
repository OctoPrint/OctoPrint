ko.bindingHandlers.slimScrolledForeach = {
    init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        return ko.bindingHandlers.foreach.init(element, valueAccessor(), allBindings, viewModel, bindingContext);
    },
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        setTimeout(function() {
            if (element.nodeName == "#comment") {
                // foreach is bound to a virtual element
                $(element.parentElement).slimScroll({scrollBy: 0});
            } else {
                $(element).slimScroll({scrollBy: 0});
            }
        }, 10);
        return ko.bindingHandlers.foreach.update(element, valueAccessor(), allBindings, viewModel, bindingContext);
    }
};
ko.virtualElements.allowedBindings.slimScrolledForeach = true;
