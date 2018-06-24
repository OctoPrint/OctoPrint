$(function() {
    var save = [];

    // Using the theme color (for the top bar), also recolor the favicon tentacle.
    function ThemeFavicon(colorname) {
        save.colorName = colorname;

        // the following is from an Apache licensed snippet:
        // http://blog.roomanna.com/09-24-2011/dynamically-coloring-a-favicon
        var link = document.querySelector("link[rel~='icon']");
        if (!link) {
          link = document.createElement("link");
          link.setAttribute("rel", "shortcut icon");
          document.head.appendChild(link);
        }

        // try to get the best quality ico possible; prefer svg, the apple-touch pngs are more difficult,
        // but all three of the others give a high-quality ico.
        var faviconUrl =
          // document.querySelector("link[rel~='apple-touch-icon'][sizes~='144x144']").href ||
          document.querySelector("link[rel~='mask-icon']").href ||
          link.href ||
          window.location.origin + "/favicon.ico";
        function onImageLoaded() {
          var icosize = 256; // example was 16
          // svgs don't really have width
          //var icosize = img.width;
          var canvas = document.createElement("canvas");
          canvas.width = icosize;
          canvas.height = icosize;
          var context = canvas.getContext("2d");
          context.drawImage(img, 0, 0, icosize, icosize);
          // https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation
          context.globalCompositeOperation = "source-in";
          //context.fillStyle = "#d00";
          context.fillStyle = save.colorName;
          context.fillRect(0, 0, icosize, icosize/1);
          context.fill();
          link.type = "image/x-icon";
          link.href = canvas.toDataURL();
        };
        var img = document.createElement("img");
        img.addEventListener("load", onImageLoaded);
        img.src = faviconUrl;
    }

    function AppearanceViewModel(parameters) {
        var self = this;

        self.name = parameters[0].appearance_name;
        self.color = parameters[0].appearance_color;
        self.colorTransparent = parameters[0].appearance_colorTransparent;

        ThemeFavicon(self.name);

        self.brand = ko.pureComputed(function() {
            if (self.name())
                return self.name();
            else
                return gettext("OctoPrint");
        });

        self.fullbrand = ko.pureComputed(function() {
            if (self.name())
                return gettext("OctoPrint") + ": " + self.name();
            else
                return gettext("OctoPrint");
        });

        self.title = ko.pureComputed(function() {
            if (self.name())
                return self.name() + " [" + gettext("OctoPrint") + "]";
            else
                return gettext("OctoPrint");
        });
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AppearanceViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["head"]
    });
});
