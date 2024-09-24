ko.bindingHandlers["click.single"] = {
    init: (element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) => {
        const handler = valueAccessor();
        const delay = 200;
        let clickTimeout = false;

        $(element).click((event) => {
            if (clickTimeout !== false) {
                clearTimeout(clickTimeout);
                clickTimeout = false;
            } else {
                clickTimeout = setTimeout(() => {
                    clickTimeout = false;
                    handler.call(viewModel, bindingContext.$data, event);
                }, delay);
            }
        });
    }
};
