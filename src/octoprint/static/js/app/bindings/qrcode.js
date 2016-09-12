ko.bindingHandlers.qrcode = {
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var val = ko.utils.unwrapObservable(valueAccessor());

        var defaultOptions = {
            text: "",
            size: 200,
            fill: "#000",
            background: null,
            label: "",
            fontname: "sans",
            fontcolor: "#000",
            radius: 0,
            ecLevel: "L"
        };

        var options = {};
        _.each(defaultOptions, function(value, key) {
            options[key] = ko.utils.unwrapObservable(val[key]) || value;
        });

        $(element).empty().qrcode(options);
    }
};
