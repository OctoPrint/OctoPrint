ko.bindingHandlers.copyWidth = {
    init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var node = ko.bindingHandlers.copyWidth._getReferenceNode(element, valueAccessor);
        ko.bindingHandlers.copyWidth._setWidth(node, element);
        ko.bindingHandlers.copyWidth._addResizeSensor(node, element);
    },
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var node = ko.bindingHandlers.copyWidth._getReferenceNode(element, valueAccessor);
        ko.bindingHandlers.copyWidth._setWidth(node, element);
        ko.bindingHandlers.copyWidth._addResizeSensor(node, element);
    },
    _setWidth: function(node, element) {
        var width = node.width();
        if (!width) return;
        if ($(element).width() === width) return;
        element.style.width = width + "px";
    },
    _getReferenceNode: function(element, valueAccessor) {
        var value = ko.utils.unwrapObservable(valueAccessor());
        if (!value) return;

        var parts = value.split(" ");
        var node = $(element);
        while (parts.length > 0) {
            var part = parts.shift();
            if (part === ":parent") {
                node = node.parent();
            } else {
                var selector = part;
                if (parts.length > 0) {
                    selector += " " + parts.join(" ");
                }
                node = $(selector, node);
                break;
            }
        }
        return node;
    },
    _addResizeSensor: function(node, element) {
        if (element.copyWidthSensor) {
            element.copyWidthSensor.detach();
            delete element.copyWidthSensor;
        }
        element.copyWidthSensor = new ResizeSensor(node, function() {
            ko.bindingHandlers.copyWidth._setWidth(node, element);
        });
    }
};

