ko.bindingHandlers["click.double"] = {
    init: (element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) => {
        const handler = valueAccessor();
        const delay = 200;
        let clicks = 0;

        $(element).click((event) => {
            clicks++;
            if (clicks === 1) {
                $(element).css("user-select", "none");
                setTimeout(() => {
                    $(element).css("user-select", "auto");
                    if (clicks === 2) {
                        handler.call(viewModel, bindingContext.$data, event);
                    }
                    clicks = 0;
                }, delay);
            }
        });
    }
};
