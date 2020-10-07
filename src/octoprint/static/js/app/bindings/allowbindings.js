ko.bindingHandlers.allowBindings = {
    init: function (elem, valueAccessor) {
        return {controlsDescendantBindings: !valueAccessor()};
    }
};
ko.virtualElements.allowedBindings.allowBindings = true;
