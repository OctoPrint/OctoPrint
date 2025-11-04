/**
 * Originally based on "Custom Control Editor", created by Marc Hannappel
 *
 * Rewritten and maintained as part of OctoPrint since 11/2024
 */

$(function () {
    const DEFAULT_COMMON = {
        name: undefined,
        width: "2",
        offset: ""
    };

    const DEFAULT_CONTROL = _.extend(_.extend({}, DEFAULT_COMMON), {
        commands: [],
        script: "",
        javascript: "",
        additionalClasses: "",
        enabled: "",
        input: [],
        regex: "",
        template: "",
        confirm: ""
    });

    const DEFAULT_CONTAINER = _.extend(_.extend({}, DEFAULT_COMMON), {
        children: [],
        layout: "vertical",
        collapsed: false
    });

    const DEFAULT_INPUT = {
        name: "",
        parameter: "",
        default: "",
        value: "",
        slider: false
    };

    const MINIMAL_CONTAINER = {
        children: [],
        layout: "vertical"
    };
    const MINIMAL_CONTROL = {
        name: "",
        commands: []
    };

    const validateAttribute = (obj, attr, def) => {
        if (obj.hasOwnProperty(attr)) {
            const val = obj[attr];
            if (_.isNumber(val)) return val;

            const parsed = parseInt(val);
            if (!isNaN(parsed)) return parsed;
        }
        return def;
    };

    const ensureProps = (obj, props) => {
        for (const prop of Object.keys(props)) {
            if (!obj.hasOwnProperty(prop)) {
                if (_.isObject(props[prop])) {
                    obj[prop] = structuredClone(props[prop]);
                } else {
                    obj[prop] = props[prop];
                }
            }
        }
    };

    const ensureObservableProps = (obj, props) => {
        for (const prop of Object.keys(props)) {
            if (_.isFunction(obj[prop])) {
                // do nothing
            } else if (_.isArray(obj[prop])) {
                obj[prop] = ko.observableArray(obj[prop]);
            } else {
                obj[prop] = ko.observable(obj[prop]);
            }
        }
    };

    const minimalizeAgainstProps = (control, defaults, minimal) => {
        for (const key of Object.keys(control)) {
            if (
                !defaults.hasOwnProperty(key) ||
                (control[key] == defaults[key] && minimal[key] === undefined)
            ) {
                delete control[key];
            }
        }
    };

    const minimalizeControl = (control) => {
        if (control.children) {
            control.children = control.children.map(minimalizeControl);
            minimalizeAgainstProps(control, DEFAULT_CONTAINER, MINIMAL_CONTAINER);
        } else {
            minimalizeAgainstProps(control, DEFAULT_CONTROL, MINIMAL_CONTROL);
        }
        return control;
    };

    const convertAndMinimalize = (controls) => {
        const objs = ko.mapping.toJS(controls);
        return objs.map(minimalizeControl);
    };

    function CustomControlManagerEditorViewModel() {
        const self = this;

        self._deferred = undefined;

        self.control = ko.observable();
        self.parent = ko.observable();
        self.editing = ko.observable(false);

        self.type = ko.observable("container");
        self.title = ko.pureComputed(() => {
            if (self.editing()) {
                if (self.type() === "container") {
                    return gettext("Create container");
                } else {
                    return gettext("Create control");
                }
            } else {
                if (self.type() === "container") {
                    return gettext("Edit container");
                } else {
                    return gettext("Edit control");
                }
            }
        });

        self.useConfirm = ko.observable(false);
        self.useOutput = ko.observable(false);
        self.useGrid = ko.pureComputed(() => {
            const parent = self.parent();
            return parent && parent.layout && parent.layout() === "horizontal_grid";
        });
        self.nameError = ko.pureComputed(() => {
            return self.type() !== "container" && !self.control().name();
        });

        self.commandsMultiline = ko.pureComputed({
            read: () => {
                if (self.control().hasOwnProperty("commands")) {
                    const commands = self.control().commands();
                    return commands.join("\n");
                }
                return "";
            },
            write: (value) => {
                if (!self.control().hasOwnProperty("commands")) return;
                self.control().commands(value.split("\n").map((x) => x.trim()));
            }
        });

        self.layouts = ko.observableArray([
            {name: gettext("Vertical"), key: "vertical"},
            {name: gettext("Horizontal"), key: "horizontal"},
            {name: gettext("Horizontal Grid"), key: "horizontal_grid"}
        ]);
        self.controlTypes = ko.observableArray([
            {name: gettext("Command"), key: "command"},
            {name: gettext("Script"), key: "script"},
            {name: gettext("Output"), key: "output"}
        ]);

        self.reset = (control, parent) => {
            if (control) {
                control = _.extend({}, control);

                parent = parent || control._parent;
                self.parent(parent);
                control._parent = undefined;

                control = structuredClone(ko.mapping.toJS(control));

                if (control.hasOwnProperty("children")) {
                    self.type("container");
                    control = _.extend(_.extend({}, DEFAULT_CONTAINER), control);
                } else {
                    if (control.output) {
                        self.type("output");
                    } else if (control.script) {
                        self.type("script");
                    } else {
                        self.type("command");
                    }
                    control = _.extend(_.extend({}, DEFAULT_CONTROL), control);
                }

                self.useConfirm(control.confirm);
                self.useOutput(control.template);

                if (control.command) {
                    control.commands = [control.command];
                }

                if (control.input) {
                    control.input = control.input.map((input) =>
                        _.extend(_.extend({}, DEFAULT_INPUT), input)
                    );
                }

                self.control(ko.mapping.fromJS(control));
            } else {
                self.type("command");
                self.parent(parent);
                self.control(ko.mapping.fromJS(DEFAULT_CONTROL));
            }
        };

        self.handleConfirm = () => {
            const obj = ko.mapping.toJS(self.control());
            const control = {};

            const copyInputs = () => {
                const result = [];
                for (const item of obj.input) {
                    const input = {
                        name: item.name,
                        parameter: item.parameter,
                        slider: false
                    };

                    if (item.slider) {
                        input.slider = {
                            min: validateAttribute(item.slider, "min", 0),
                            max: validateAttribute(item.slider, "max", 255),
                            step: validateAttribute(item.slider, "step", 1)
                        };
                        input.default = validateAttribute(
                            item,
                            "default",
                            input.slider.min
                        );
                    } else {
                        input.default = item.default || "";
                    }

                    input.value = input.default;

                    result.push(input);
                }
                control.input = result;
            };

            const copyOutput = () => {
                control.regex = obj.regex;
                control.template = obj.template;
            };

            switch (self.type()) {
                case "container": {
                    control.name = obj.name;
                    control.layout = obj.layout;
                    control.children = [];
                    control.collapsed = obj.collapsed;
                    break;
                }

                case "command": {
                    control.name = obj.name;
                    control.commands = obj.commands;

                    if (obj.input) {
                        copyInputs();
                    }

                    if (self.useConfirm()) {
                        control.confirm = obj.confirm;
                    }

                    if (self.useOutput()) {
                        copyOutput();
                    }

                    break;
                }

                case "script": {
                    control.name = obj.name;
                    control.script = obj.script;

                    if (obj.input) {
                        copyInputs();
                    }

                    if (self.useConfirm()) {
                        control.confirm = obj.confirm;
                    }

                    break;
                }

                case "output": {
                    copyOutput();
                    break;
                }
            }

            control.width = obj.width;
            control.offset = obj.offset;

            if (self._deferred) {
                self._deferred.resolve(control);
                self._deferred = undefined;
            }

            self.hide();
        };

        self.showContainer = (container, parent) => {
            const editing = !!container;
            container = container || _.extend({}, DEFAULT_CONTAINER);
            return self.show(container, editing, parent);
        };

        self.showControl = (control, parent) => {
            const editing = !!control;
            control = control || _.extend({}, DEFAULT_CONTROL);
            return self.show(control, editing, parent);
        };

        self.show = (control, editing, parent) => {
            if (self._deferred) {
                self._deferred.reject();
            }
            self._deferred = $.Deferred();

            log.debug("Showing control in editor:", ko.mapping.toJS(control));
            self.editing(editing);
            self.reset(control, parent);

            self.dialog.modal("show");

            return self._deferred.promise();
        };

        self.hide = () => {
            self.dialog.modal("hide");
        };

        self.removeInput = (data) => {
            self.control().input.remove(data);
        };

        self.addInput = () => {
            const input = {
                name: ko.observable(""),
                parameter: ko.observable(""),
                value: ko.observable(""),
                slider: false
            };

            self.control().input.push(input);
        };

        self.addSliderInput = () => {
            const obj = {
                name: ko.observable(""),
                parameter: ko.observable(""),
                value: ko.observable(),
                slider: {
                    min: ko.observable(),
                    max: ko.observable(),
                    step: ko.observable()
                }
            };

            self.control().input.push(obj);
        };

        self.onStartup = () => {
            self.dialog = $("#customcontrolmanager-editor");
            self.dialog.on("hidden", () => {
                if (self.deferred) {
                    self.deferred.reject();
                    self.deferred = undefined;
                }
            });
            self.reset();
        };
    }

    function CustomControlManagerViewModel(parameters) {
        const self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];
        self.settings = parameters[2];
        self.controlVM = parameters[3];

        self.controls = ko.observableArray([]);
        self.editor = new CustomControlManagerEditorViewModel();

        self._dirty = false;

        self.requestData = () => {
            OctoPrint.control.getCustomControls().done(self.fromResponse);
        };

        self.fromResponse = (response) => {
            const controls = response.controls.filter((item) => item.source === "config");
            self._processControls(controls, "control");
            self.controls(controls);
            self._dirty = false;
        };

        self.getTemplate = (control) => {
            if (control.hasOwnProperty("children")) {
                if (control.name()) {
                    return "customcontrolmanager-container-collapsable";
                } else {
                    return "customcontrolmanager-container-nameless";
                }
            } else {
                return "customcontrolmanager-control";
            }
        };

        self.rowCss = (control) => {
            return self.controlVM.rowCss(ko.mapping.toJS(control));
        };

        self.addContainer = (parent) => {
            self.editor.showContainer(null, parent).done((container) => {
                self._processControl(container, "temp", parent);
                if (parent) {
                    parent.children.push(container);
                } else {
                    self.controls.push(container);
                }
                self._updateControlIds();
                self._dirty = true;
            });
        };

        self.addControl = (parent) => {
            self.editor.showControl(null, parent).done((control) => {
                self._processControl(control, "temp", parent);
                if (parent) {
                    parent.children.push(control);
                } else {
                    self.controls.push(control);
                }
                self._updateControlIds();
                log.debug("Added control: ", ko.mapping.toJS(control));
                self._dirty = true;
            });
        };

        self.editControl = (control) => {
            self.editor.show(control).done((edited) => {
                log.debug("Edited control: ", edited);

                if (edited.hasOwnProperty("children")) {
                    edited = _.extend(_.extend({}, DEFAULT_CONTAINER), edited);
                } else {
                    edited = _.extend(_.extend({}, DEFAULT_CONTROL), edited);
                }

                control.name(edited.name);
                control.width(edited.width);
                control.offset(edited.offset);

                if (control.hasOwnProperty("children")) {
                    // handle container
                    control.layout(edited.layout);
                    control.collapsed(!!edited.collapsed);
                } else {
                    // handle control
                    control.commands(edited.commands);
                    control.script(edited.script);
                    control.javascript(edited.javascript);
                    control.additionalClasses(edited.additionalClasses);
                    control.enabled(edited.enabled);
                    control.regex(edited.regex);
                    control.template(edited.template);
                    control.confirm(edited.confirm);

                    while (control.input().length > edited.input.length) {
                        control.input.pop();
                    }
                    for (let i = 0; i < edited.input.length; i++) {
                        if (i < control.input().length) {
                            control.input()[i].name(edited.input[i].name);
                            control.input()[i].parameter(edited.input[i].parameter);
                            control.input()[i].default(edited.input[i].default);
                            control.input()[i].value(edited.input[i].value);
                            if (edited.input[i].slider) {
                                control.input()[i].slider(edited.input[i].slider);
                            }
                        } else {
                            control.input.push(ko.mapping.fromJS(edited.input[i]));
                        }
                    }
                }

                log.debug("Updated control: ", ko.mapping.toJS(control));
                self._dirty = true;
            });
        };

        self.deleteControl = (control) => {
            const process = () => {
                if (control._parent) {
                    // somewhere in the tree
                    control._parent.children.remove((node) => node._id === control._id);
                } else {
                    // top level node
                    self.controls.remove((node) => node._id === control._id);
                }
                self._updateControlIds();
                self._dirty = true;
            };

            showConfirmationDialog(
                _.sprintf(
                    gettext("You are about to delete the custom control with id %(id)s."),
                    {id: control._id}
                ),
                process
            );
        };

        self._processControls = (controls, prefix, parent) => {
            _.each(controls, (control, idx) => {
                self._processControl(control, prefix + "-" + (idx + 1), parent);
            });
        };

        self._processControl = (control, prefix, parent) => {
            prefix = prefix || "";

            control._id = prefix;
            control._parent = parent;

            ensureProps(control, DEFAULT_COMMON);

            if (control.hasOwnProperty("children")) {
                ensureProps(control, DEFAULT_CONTAINER);
                self._processControls(control.children, prefix, control);
                ensureObservableProps(control, DEFAULT_CONTAINER);
            } else {
                ensureProps(control, DEFAULT_CONTROL);

                _.each(control.input, (input) => {
                    ensureProps(input, DEFAULT_INPUT);

                    if (input.hasOwnProperty("slider") && _.isObject(input.slider)) {
                        input.slider.min = validateAttribute(input.slider, "min", 0);
                        input.slider.max = validateAttribute(input.slider, "max", 255);
                        input.slider.step = validateAttribute(input.slider, "step", 1);

                        let defaultVal = validateAttribute(
                            input,
                            "default",
                            input.slider.min
                        );
                        if (!_.inRange(defaultVal, input.slider.min, input.slider.max)) {
                            defaultVal =
                                defaultVal < input.slider.min
                                    ? input.slider.min
                                    : input.slider.max;
                        }

                        input.default = defaultVal;
                    } else {
                        input.slider = false;
                    }
                    input.value = input.default;

                    ensureObservableProps(input, DEFAULT_INPUT);
                });

                ensureObservableProps(control, DEFAULT_CONTROL);
            }

            ensureObservableProps(control, DEFAULT_COMMON);
        };

        self._updateControlIds = (controls, prefix) => {
            controls = controls || self.controls();
            prefix = prefix || "control";
            for (let idx = 0; idx < controls.length; idx++) {
                const control = controls[idx];
                control._id = prefix + "-" + (idx + 1);
                if (control.children) {
                    self._updateControlIds(control.children(), control._id);
                }
            }
        };

        self.onStartup = () => {
            self.editor.onStartup();
        };

        self.onSettingsShown = () => {
            self.requestData();
        };

        self.onSettingsBeforeSave = () => {
            if (!self.loginState.hasPermission(self.access.permissions.SETTINGS)) {
                return;
            }

            if (!self._dirty) return;

            const controls = convertAndMinimalize(self.controls());
            self.settings.settings.controls(
                controls.map((control) => ko.mapping.fromJS(control))
            );
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: CustomControlManagerViewModel,
        dependencies: [
            "loginStateViewModel",
            "accessViewModel",
            "settingsViewModel",
            "controlViewModel"
        ],
        elements: ["#settings_plugin_customcontrolmanager"]
    });
});
