ko.bindingHandlers.marquee = {
    init: function (element, valueAccessor, allBindingsAccessor, context) {
        const getSize = (element) => {
            const container = $("<div></div>");
            container.css({
                "position": "absolute",
                "left:": "-1000px",
                "top:": "-1000px",
                "width": "auto",
                "height": "auto"
            });

            container.append(element.clone());
            $(document.body).append(container);
            const rect = {width: container.width(), height: container.height()};
            container.remove();

            return rect;
        };

        const value = valueAccessor();
        const valueUnwrapped = ko.unwrap(value);

        const $element = $(element);

        $element.addClass(valueUnwrapped.class);
        $element
            .on("mouseenter", function () {
                const width = getSize($element).width;
                const distance = width - $element.width();

                if (distance <= 0) return;

                const speed = valueUnwrapped.speed || 100; // px/sec
                const time = distance / speed;

                $element.css({
                    "margin-left": "-" + distance + "px",
                    "transition-duration": time + "s"
                });
            })
            .on("mouseleave", function () {
                $element.css({
                    "margin-left": "0"
                });
            });
    }
};
