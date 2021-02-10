ko.bindingHandlers.valueWithInit = {
    init: function (element, valueAccessor, allBindingsAccessor, context) {
        var observable = valueAccessor();
        var value = element.value;

        observable(value);

        ko.bindingHandlers.value.init(
            element,
            valueAccessor,
            allBindingsAccessor,
            context
        );
    },
    update: ko.bindingHandlers.value.update
};
