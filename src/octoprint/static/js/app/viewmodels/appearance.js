$(function () {
    var save = {};

    // Using the theme color (for the top bar), also recolor the favicon tentacle.
    function themeFavicon(colorname) {
        save.colorName = colorname;

        // the following is from an Apache licensed snippet:
        // http://blog.roomanna.com/09-24-2011/dynamically-coloring-a-favicon
        var link = document.querySelector("link[rel='shortcut icon']");
        if (!link) {
            link = document.createElement("link");
            link.setAttribute("rel", "shortcut icon");
            document.head.appendChild(link);
        }

        // try to get the best quality ico possible; prefer svg, the apple-touch pngs are more difficult,
        // but all three of the others give a high-quality ico.
        var faviconUrl =
            document.querySelector("link[rel~='mask-icon-theme']").href ||
            link.href ||
            window.location.origin + "/favicon.ico";

        function onImageLoaded() {
            var icosize = 256;

            var canvas = document.createElement("canvas");
            canvas.width = icosize;
            canvas.height = icosize;

            var context = canvas.getContext("2d");

            function grayscale() {
                var imageData = context.getImageData(0, 0, canvas.width, canvas.height),
                    pixels = imageData.data,
                    i,
                    l,
                    r,
                    g,
                    b,
                    a,
                    luma;

                for (i = 0, l = pixels.length; i < l; i += 4) {
                    a = pixels[i + 3];
                    if (a === 0) {
                        continue;
                    }

                    r = pixels[i];
                    g = pixels[i + 1];
                    b = pixels[i + 2];

                    luma = r * 0.2126 + g * 0.7152 + b * 0.0722;

                    pixels[i] = pixels[i + 1] = pixels[i + 2] = luma;
                }

                context.putImageData(imageData, 0, 0);
            }

            function colorize(color, alpha) {
                context.globalCompositeOperation = "source-atop";
                context.globalAlpha = alpha;
                context.fillStyle = color;
                context.fillRect(0, 0, canvas.width, canvas.height);
                context.globalCompositeOperation = "source-over";
                context.globalAlpha = 1.0;
            }

            context.drawImage(img, 0, 0, canvas.width, canvas.height);
            if (save.colorName !== "default") {
                grayscale();
                colorize(save.colorName, 0.3);
            }
            link.type = "image/x-icon";
            link.href = canvas.toDataURL();
        }

        var img = document.createElement("img");
        img.addEventListener("load", onImageLoaded);
        img.src = faviconUrl;
    }

    function AppearanceViewModel(parameters) {
        var self = this;

        self.name = parameters[0].appearance_name;
        self.color = parameters[0].appearance_color;
        self.colorTransparent = parameters[0].appearance_colorTransparent;
        self.colorIcon = parameters[0].appearance_colorIcon;

        function updateIcon() {
            if (self.colorIcon()) {
                themeFavicon(self.color());
            } else {
                themeFavicon("default");
            }
        }
        self.color.subscribe(updateIcon);
        self.colorIcon.subscribe(updateIcon);
        updateIcon();

        self.brand = ko.pureComputed(function () {
            if (self.name()) return self.name();
            else return gettext("OctoPrint");
        });

        self.fullbrand = ko.pureComputed(function () {
            if (self.name()) return gettext("OctoPrint") + ": " + self.name();
            else return gettext("OctoPrint");
        });

        self.title = ko.pureComputed(function () {
            if (self.name()) return self.name() + " [" + gettext("OctoPrint") + "]";
            else return gettext("OctoPrint");
        });

        self.theme_color = ko.pureComputed(function () {
            switch (self.color()) {
                case "red":
                    return "#bb645f";
                case "orange":
                    return "#e39665";
                case "yellow":
                    return "#e3d765;";
                case "green":
                    return "#98f064";
                case "blue":
                    return "#2e63cc";
                case "violet":
                    return "#9864f0";
                case "black":
                    return "#4f4f4f";
                case "white":
                    return "#e9e9e9";
                case "default":
                default:
                    return "#ebebeb";
            }
        });
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AppearanceViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["head"]
    });
});
