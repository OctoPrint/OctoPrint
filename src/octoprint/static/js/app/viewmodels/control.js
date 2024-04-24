$(function () {
    function ControlViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.access = parameters[2];

        self._createToolEntry = function () {
            return {
                name: ko.observable(),
                key: ko.observable()
            };
        };

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.extrusionAmount = ko.observable(undefined);

        self.controls = ko.observableArray([]);

        self.distances = ko.observableArray([0.1, 1, 10, 100]);
        self.distance = ko.observable(10);

        self.tools = ko.observableArray([]);

        self.feedRate = ko.observable();
        self.flowRate = ko.observable();

        self.feedbackControlLookup = {};

        self.controlsFromServer = [];
        self.additionalControls = [];
        self.intersectionObservers = [];

        self.keycontrolActive = ko.observable(false);
        self.keycontrolHelpActive = ko.observable(false);
        self.keycontrolPossible = ko.pureComputed(function () {
            return (
                self.loginState.hasPermission(self.access.permissions.CONTROL) &&
                self.settings.feature_keyboardControl() &&
                self.isOperational() &&
                !self.isPrinting() &&
                !$.browser.mobile
            );
        });
        self.showKeycontrols = ko.pureComputed(function () {
            return self.keycontrolPossible();
        });

        self._visibleWebcam = undefined;

        self._dispatchWebcamRefresh = function (target) {
            log.debug(`Webcam refresh triggered for #${target.id}`);
            var vm = ko.dataFor(target.children[0]);
            if (vm === self) {
                log.debug(`VM for webcam #${target.id} is not bound, skipping refresh`);
            } else if (vm === undefined) {
                log.debug(`VM for webcam #${target.id} not found, skipping refresh`);
            } else if (typeof vm.onWebcamRefresh === "function") {
                vm.onWebcamRefresh();
            } else {
                log.debug(
                    `VM for webcam #${target.id} does not declare 'onWebcamRefresh()', skipping refresh (vm=${vm.constructor.name})`
                );
            }
        };

        self._dispatchWebcamVisibilityChange = function (target, visible) {
            log.debug(`Webcam visibility of #${target.id} changed to ${visible}`);
            var vm = ko.dataFor(target.children[0]);
            if (vm === self) {
                log.debug(
                    `VM for webcam #${target.id} is not bound, skipping visibility update`
                );
            } else if (vm === undefined) {
                log.debug(
                    `VM for webcam #${target.id} not found, skipping visibility update`
                );
            } else if (typeof vm.onWebcamVisibilityChange === "function") {
                vm.onWebcamVisibilityChange(visible);
            } else {
                log.debug(
                    `VM for webcam #${target.id} does not declare 'onWebcamVisibilityChange(visible)', skipping visibility update (vm=${vm.constructor.name})`
                );
            }
        };

        const selectedCameraStorageKey = "core.control.selectedCamera";
        self.selectDefaultWebcam = function () {
            if (!document.querySelector("#webcam_plugins_container .nav")) {
                // we only have one webcam plugin, select that and be done (note: this bypasses local storage)
                $("#webcam-group .tab-pane:first").addClass("active");
                return;
            }

            let div = localStorage[selectedCameraStorageKey];

            if (!div || document.getElementById(div.slice(1)) === null) {
                div = undefined;
            }

            if (div !== undefined) {
                $(`${div}_link a`).tab("show");
            } else {
                $("#webcam_plugins_container .nav li:first a").tab("show");
            }
        };

        self.onStartupComplete = function () {
            $("#webcam_plugins_container .nav a[data-toggle='tab']").on("shown", (e) => {
                localStorage[selectedCameraStorageKey] = e.target.hash;
            });
            self.selectDefaultWebcam();
            self.recreateIntersectionObservers();
        };

        self.recreateIntersectionObservers = function () {
            // We are using the IntersectionObserver API to determine whether a webcam is visible or not.
            // A webcam will not intersect with the control tab if the control tab is invisible because another tab
            // is selected or if the webcam isn't shown because another webcam is active.
            //
            // Whenever the webacam changes visibility we will call onWebcamVisibilityChange() which the webcam's
            //  VM can use to start or stop the stream.
            self.intersectionObservers.forEach(function (observer) {
                observer.disconnect();
            });
            self.intersectionObservers = [];

            document
                .querySelectorAll("#webcam-group .tab-pane")
                .forEach(function (target) {
                    var options = {
                        root: document.querySelector("#webcam_plugins_container"),
                        rootMargin: "0px",
                        threshold: 0.01
                    };
                    var callback = function (entries) {
                        var visible = entries[0].isIntersecting;
                        self._dispatchWebcamVisibilityChange(target, visible);

                        // Keep track which webcam is currently visible (if any)
                        if (visible) {
                            self._visibleWebcam = target;
                        } else if (self._visibleWebcam === target && !visible) {
                            self._visibleWebcam = undefined;
                        }
                    };

                    var observer = new IntersectionObserver(callback, options);
                    observer.observe(target);
                    self.intersectionObservers.push(observer);
                });
        };

        self.onBrowserTabVisibilityChange = function (tabVisible) {
            // We also observe the browser tab. If any webcam is currently visible, we will update
            // it with the tab status as well.
            if (self._visibleWebcam !== undefined) {
                self._dispatchWebcamVisibilityChange(self._visibleWebcam, tabVisible);
            }
        };

        self.refreshWebcam = function () {
            if (self._visibleWebcam !== undefined) {
                self._dispatchWebcamRefresh(self._visibleWebcam);
            }
        };

        self.settings.printerProfiles.currentProfileData.subscribe(function () {
            self._updateExtruderCount();
            self._updateExtrusionAmount();

            const data = self.settings.printerProfiles.currentProfileData();
            if (data && data.extruder) {
                if (data.extruder.defaultExtrusionLength) {
                    data.extruder.defaultExtrusionLength.subscribe(
                        self._updateExtrusionAmount
                    );
                }
                if (data.extruder.count) {
                    data.extruder.count.subscribe(self._updateExtruderCount);
                }
            }
            self.settings.printerProfiles
                .currentProfileData()
                .extruder.count.subscribe(self._updateExtruderCount);
        });
        self._updateExtrusionAmount = function () {
            const data = self.settings.printerProfiles.currentProfileData();
            if (!data || !data.extruder) {
                return;
            }
            self.extrusionAmount(
                self.settings.printerProfiles
                    .currentProfileData()
                    .extruder.defaultExtrusionLength()
            );
        };
        self._updateExtruderCount = function () {
            const data = self.settings.printerProfiles.currentProfileData();
            if (!data || !data.extruder || !data.extruder.count) {
                return;
            }
            var tools = [];

            var numExtruders = self.settings.printerProfiles
                .currentProfileData()
                .extruder.count();
            if (numExtruders > 1) {
                // multiple extruders
                for (var extruder = 0; extruder < numExtruders; extruder++) {
                    tools[extruder] = self._createToolEntry();
                    tools[extruder]["name"](gettext("Tool") + " " + extruder);
                    tools[extruder]["key"]("tool" + extruder);
                }
            } else if (numExtruders === 1) {
                // only one extruder, no need to add numbers
                tools[0] = self._createToolEntry();
                tools[0]["name"](gettext("Hotend"));
                tools[0]["key"]("tool0");
            }

            self.tools(tools);
        };

        self.fromCurrentData = function (data) {
            self._processStateData(data.state);
        };

        self.fromHistoryData = function (data) {
            self._processStateData(data.state);
        };

        self._processStateData = function (data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
        };

        self.onEventSettingsUpdated = function () {
            self.requestData();
        };

        self.onEventRegisteredMessageReceived = function (payload) {
            if (payload.key in self.feedbackControlLookup) {
                var outputs = self.feedbackControlLookup[payload.key];
                _.each(payload.outputs, function (value, key) {
                    if (outputs.hasOwnProperty(key)) {
                        outputs[key](value);
                    }
                });
            }
        };

        self.rerenderControls = function () {
            var allControls = self.controlsFromServer.concat(self.additionalControls);
            self.controls(self._processControls(allControls));
        };

        self.requestData = function () {
            if (!self.loginState.hasPermission(self.access.permissions.CONTROL)) {
                return;
            }

            OctoPrint.control.getCustomControls().done(function (response) {
                self._fromResponse(response);
            });
        };

        self._fromResponse = function (response) {
            self.controlsFromServer = response.controls;
            self.rerenderControls();
        };

        self._processControls = function (controls) {
            for (var i = 0; i < controls.length; i++) {
                controls[i] = self._processControl(controls[i]);
            }
            return controls;
        };

        self._processControl = function (control) {
            if (control.hasOwnProperty("processed") && control.processed) {
                return control;
            }

            if (
                control.hasOwnProperty("template") &&
                control.hasOwnProperty("key") &&
                control.hasOwnProperty("template_key") &&
                !control.hasOwnProperty("output")
            ) {
                control.output = ko.observable(control.default || "");
                if (!self.feedbackControlLookup.hasOwnProperty(control.key)) {
                    self.feedbackControlLookup[control.key] = {};
                }
                self.feedbackControlLookup[control.key][control.template_key] =
                    control.output;
            }

            if (control.hasOwnProperty("children")) {
                control.children = ko.observableArray(
                    self._processControls(control.children)
                );
                if (
                    !control.hasOwnProperty("layout") ||
                    !(
                        control.layout == "vertical" ||
                        control.layout == "horizontal" ||
                        control.layout == "horizontal_grid"
                    )
                ) {
                    control.layout = "vertical";
                }

                if (!control.hasOwnProperty("collapsed")) {
                    control.collapsed = false;
                }
            }

            if (control.hasOwnProperty("input")) {
                var attributeToInt = function (obj, key, def) {
                    if (obj.hasOwnProperty(key)) {
                        var val = obj[key];
                        if (_.isNumber(val)) {
                            return val;
                        }

                        var parsedVal = parseInt(val);
                        if (!isNaN(parsedVal)) {
                            return parsedVal;
                        }
                    }
                    return def;
                };

                _.each(control.input, function (element) {
                    if (element.hasOwnProperty("slider") && _.isObject(element.slider)) {
                        element.slider["min"] = attributeToInt(element.slider, "min", 0);
                        element.slider["max"] = attributeToInt(
                            element.slider,
                            "max",
                            255
                        );

                        // try defaultValue, default to min
                        var defaultValue = attributeToInt(
                            element,
                            "default",
                            element.slider.min
                        );

                        // if default value is not w/i range of min and max, correct that
                        if (
                            !_.inRange(
                                defaultValue,
                                element.slider.min,
                                element.slider.max
                            )
                        ) {
                            // use bound closer to configured default value
                            defaultValue =
                                defaultValue < element.slider.min
                                    ? element.slider.min
                                    : element.slider.max;
                        }

                        element.value = ko.observable(defaultValue);
                    } else {
                        element.slider = false;
                        element.value = ko.observable(
                            element.hasOwnProperty("default")
                                ? element["default"]
                                : undefined
                        );
                    }
                });
            }

            if (control.hasOwnProperty("javascript")) {
                var js = control.javascript;

                // if js is a function everything's fine already, but if it's a string
                // we need to eval that first
                if (!_.isFunction(js)) {
                    control.javascript = function (data) {
                        eval(js);
                    };
                }
            }

            if (control.hasOwnProperty("enabled")) {
                var enabled = control.enabled;

                // if js is a function everything's fine already, but if it's a string
                // we need to eval that first
                if (!_.isFunction(enabled)) {
                    control.enabled = function (data) {
                        return eval(enabled);
                    };
                }
            }

            if (!control.hasOwnProperty("additionalClasses")) {
                control.additionalClasses = "";
            }

            control.processed = true;
            return control;
        };

        self.isCustomEnabled = function (data) {
            if (data.hasOwnProperty("enabled")) {
                return data.enabled(data);
            } else {
                return (
                    self.loginState.hasPermission(self.access.permissions.CONTROL) &&
                    self.isOperational()
                );
            }
        };

        self.clickCustom = function (data) {
            var callback;
            if (data.hasOwnProperty("javascript")) {
                callback = data.javascript;
            } else {
                callback = self.sendCustomCommand;
            }

            if (data.confirm) {
                showConfirmationDialog({
                    message: data.confirm,
                    onproceed: function (e) {
                        callback(data);
                    }
                });
            } else {
                callback(data);
            }
        };

        self.sendJogCommand = function (axis, multiplier, distance) {
            if (typeof distance === "undefined") distance = self.distance();
            if (
                self.settings.printerProfiles.currentProfileData() &&
                self.settings.printerProfiles.currentProfileData()["axes"] &&
                self.settings.printerProfiles.currentProfileData()["axes"][axis] &&
                self.settings.printerProfiles
                    .currentProfileData()
                    ["axes"][axis]["inverted"]()
            ) {
                multiplier *= -1;
            }

            var data = {};
            data[axis] = distance * multiplier;
            OctoPrint.printer.jog(data);
        };

        self.sendHomeCommand = function (axis) {
            OctoPrint.printer.home(axis);
        };

        self.feedRateBusy = ko.observable(false);
        self.feedRateResetter = ko.observable();
        self.sendFeedRateCommand = function () {
            var rate = self.feedRate();
            if (!rate) return;

            rate = _.parseInt(self.feedRate());
            self.feedRateBusy(true);
            OctoPrint.printer
                .setFeedrate(rate)
                .done(function () {
                    self.feedRate(undefined);
                })
                .always(function () {
                    self.feedRateBusy(false);
                });
        };
        self.resetFeedRateDisplay = function () {
            self.cancelFeedRateDisplayReset();
            self.feedRateResetter(
                setTimeout(function () {
                    self.feedRate(undefined);
                    self.feedRateResetter(undefined);
                }, 5000)
            );
        };
        self.cancelFeedRateDisplayReset = function () {
            var resetter = self.feedRateResetter();
            if (resetter) {
                clearTimeout(resetter);
                self.feedRateResetter(undefined);
            }
        };

        self.sendExtrudeCommand = function () {
            self._sendECommand(1);
        };

        self.sendRetractCommand = function () {
            self._sendECommand(-1);
        };

        self.flowRateBusy = ko.observable(false);
        self.flowRateResetter = ko.observable();
        self.sendFlowRateCommand = function () {
            var rate = self.flowRate();
            if (!rate) return;

            rate = _.parseInt(self.flowRate());
            self.flowRateBusy(true);
            OctoPrint.printer
                .setFlowrate(rate)
                .done(function () {
                    self.flowRate(undefined);
                })
                .always(function () {
                    self.flowRateBusy(false);
                });
        };
        self.resetFlowRateDisplay = function () {
            self.cancelFlowRateDisplayReset();
            self.flowRateResetter(
                setTimeout(function () {
                    self.flowRate(undefined);
                    self.flowRateResetter(undefined);
                }, 5000)
            );
        };
        self.cancelFlowRateDisplayReset = function () {
            var resetter = self.flowRateResetter();
            if (resetter) {
                clearTimeout(resetter);
                self.flowRateResetter(undefined);
            }
        };

        self._sendECommand = function (dir) {
            var length = self.extrusionAmount();
            OctoPrint.printer.extrude(length * dir);
        };

        self.sendSelectToolCommand = function (data) {
            if (!data || !data.key()) return;

            OctoPrint.printer.selectTool(data.key());
        };

        self.sendCustomCommand = function (command) {
            if (!command) return;

            var parameters = {};
            if (command.hasOwnProperty("input")) {
                _.each(command.input, function (input) {
                    if (
                        !input.hasOwnProperty("parameter") ||
                        !input.hasOwnProperty("value")
                    ) {
                        return;
                    }

                    parameters[input.parameter] = input.value();
                });
            }

            if (command.hasOwnProperty("command") || command.hasOwnProperty("commands")) {
                var commands = command.commands || [command.command];
                OctoPrint.control.sendGcodeWithParameters(commands, parameters);
            } else if (command.hasOwnProperty("script")) {
                var script = command.script;
                var context = command.context || {};
                OctoPrint.control.sendGcodeScriptWithParameters(
                    script,
                    context,
                    parameters
                );
            }
        };

        self.displayMode = function (customControl) {
            if (customControl.hasOwnProperty("children")) {
                if (customControl.name) {
                    return "customControls_containerTemplate_collapsable";
                } else {
                    return "customControls_containerTemplate_nameless";
                }
            } else {
                return "customControls_controlTemplate";
            }
        };

        self.rowCss = function (customControl) {
            var span = "span2";
            var offset = "";
            if (customControl.hasOwnProperty("width")) {
                span = "span" + customControl.width;
            }
            if (customControl.hasOwnProperty("offset")) {
                offset = "offset" + customControl.offset;
            }
            return span + " " + offset;
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.requestData();
                };

        self.onAllBound = function (allViewModels) {
            var additionalControls = [];
            callViewModels(allViewModels, "getAdditionalControls", function (method) {
                additionalControls = additionalControls.concat(method());
            });
            if (additionalControls.length > 0) {
                self.additionalControls = additionalControls;
                self.rerenderControls();
            }
        };

        self.onFocus = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            self.keycontrolActive(true);
        };

        self.onMouseOver = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            $("#webcam_plugins_container").focus();
            self.keycontrolActive(true);
        };

        self.onMouseOut = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;
            $("#webcam_plugins_container").blur();
            self.keycontrolActive(false);
        };

        self.toggleKeycontrolHelp = function () {
            self.keycontrolHelpActive(!self.keycontrolHelpActive());
        };

        self.onKeyDown = function (data, event) {
            if (!self.settings.feature_keyboardControl()) return;

            var button = undefined;
            var visualizeClick = true;

            switch (event.which) {
                case 37: // left arrow key
                    // X-
                    button = $("#control-xdec");
                    break;
                case 38: // up arrow key
                    // Y+
                    button = $("#control-yinc");
                    break;
                case 39: // right arrow key
                    // X+
                    button = $("#control-xinc");
                    break;
                case 40: // down arrow key
                    // Y-
                    button = $("#control-ydec");
                    break;
                case 49: // number 1
                case 97: // numpad 1
                    // Distance 0.1
                    button = $("#control-distance01");
                    visualizeClick = false;
                    break;
                case 50: // number 2
                case 98: // numpad 2
                    // Distance 1
                    button = $("#control-distance1");
                    visualizeClick = false;
                    break;
                case 51: // number 3
                case 99: // numpad 3
                    // Distance 10
                    button = $("#control-distance10");
                    visualizeClick = false;
                    break;
                case 52: // number 4
                case 100: // numpad 4
                    // Distance 100
                    button = $("#control-distance100");
                    visualizeClick = false;
                    break;
                case 33: // page up key
                case 87: // w key
                    // z lift up
                    button = $("#control-zinc");
                    break;
                case 34: // page down key
                case 83: // s key
                    // z lift down
                    button = $("#control-zdec");
                    break;
                case 36: // home key
                    // xy home
                    button = $("#control-xyhome");
                    break;
                case 35: // end key
                    // z home
                    button = $("#control-zhome");
                    break;
                case 9: // prevent tab key from removing focus from webcam
                    event.preventDefault();
                    return false;
                default:
                    // don't prevent other keys
                    return true;
            }

            if (button === undefined) {
                return false;
            } else {
                event.preventDefault();
                if (visualizeClick) {
                    button.addClass("active");
                    setTimeout(function () {
                        button.removeClass("active");
                    }, 150);
                }
                button.click();
            }
        };

        self.stripDistanceDecimal = function (distance) {
            return distance.toString().replace(".", "");
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ControlViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel", "accessViewModel"],
        elements: ["#control", "#control_link"]
    });
});
