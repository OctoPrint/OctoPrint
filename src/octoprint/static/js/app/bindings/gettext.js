ko.bindingHandlers.gettext = {
    init: function () {
        // Prevent binding on the dynamically-injected text node (as developers are unlikely to expect that, and it has security implications).
        // It should also make things faster, as we no longer have to consider whether the text node might be bindable.
        return {controlsDescendantBindings: true};
    },
    update: function (element, valueAccessor) {
        var gt =
            gettext ||
            function (text) {
                return text;
            };
        ko.utils.setTextContent(element, gt(valueAccessor()));
    }
};
ko.virtualElements.allowedBindings["gettext"] = true;
