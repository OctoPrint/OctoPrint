ko.bindingHandlers.slimScrolledForeach = {
    makeTemplateValueAccessor: function (valueAccessor) {
        var modelValue = valueAccessor(),
            unwrappedValue = ko.utils.peekObservable(modelValue), // Unwrap without setting a dependency here
            result,
            slimscroll;

        // If unwrappedValue is the array, pass in the wrapped value on its own
        // The value will be unwrapped and tracked within the template binding
        // (See https://github.com/SteveSanderson/knockout/issues/523)
        if (!unwrappedValue || typeof unwrappedValue.length === "number") {
            result = {
                foreach: modelValue,
                templateEngine: ko.nativeTemplateEngine.instance
            };
            slimscroll = {};
        } else {
            // If unwrappedValue.data is the array, preserve all relevant options and unwrap again value so we get updates
            ko.utils.unwrapObservable(modelValue);
            result = {
                foreach: unwrappedValue["data"],
                as: unwrappedValue["as"],
                includeDestroyed: unwrappedValue["includeDestroyed"],
                afterAdd: unwrappedValue["afterAdd"],
                beforeRemove: unwrappedValue["beforeRemove"],
                afterRender: unwrappedValue["afterRender"],
                beforeMove: unwrappedValue["beforeMove"],
                afterMove: unwrappedValue["afterMove"],
                templateEngine: ko.nativeTemplateEngine.instance
            };
            slimscroll = unwrappedValue["slimscroll"];
        }

        return {
            accessor: function () {
                return result;
            },
            slimscroll: slimscroll
        };
    },

    slimscroll: function (element, options) {
        options = options || {};
        setTimeout(function () {
            if (element.nodeName === "#comment") {
                // foreach is bound to a virtual element
                $(element.parentElement).slimScroll(options);
            } else {
                $(element).slimScroll(options);
            }
        }, 10);
    },

    init: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
        var prepped =
            ko.bindingHandlers["slimScrolledForeach"].makeTemplateValueAccessor(
                valueAccessor
            );
        ko.bindingHandlers["slimScrolledForeach"].slimscroll(element, prepped.slimscroll);
        return ko.bindingHandlers["template"]["init"](element, prepped.accessor);
    },
    update: function (element, valueAccessor, allBindings, viewModel, bindingContext) {
        var prepped =
            ko.bindingHandlers["slimScrolledForeach"].makeTemplateValueAccessor(
                valueAccessor
            );
        var options = $.extend(prepped.slimscroll, {scrollBy: 0});
        ko.bindingHandlers["slimScrolledForeach"].slimscroll(element, options);
        return ko.bindingHandlers["template"]["update"](
            element,
            prepped.accessor,
            allBindings,
            viewModel,
            bindingContext
        );
    }
};
ko.virtualElements.allowedBindings.slimScrolledForeach = true;
