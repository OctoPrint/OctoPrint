$(function() {
    function TerminalViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.tabActive = false;

        self.log = ko.observableArray([]);
        self.log.extend({ throttle: 500 });
        self.plainLogLines = ko.observableArray([]);
        self.plainLogLines.extend({ throttle: 500 });

        self.buffer = ko.observable(300);
        self.upperLimit = ko.observable(1499);

        self.command = ko.observable(undefined);

        self.isErrorOrClosed = ko.observable(undefined);
        self.isOperational = ko.observable(undefined);
        self.isPrinting = ko.observable(undefined);
        self.isPaused = ko.observable(undefined);
        self.isError = ko.observable(undefined);
        self.isReady = ko.observable(undefined);
        self.isLoading = ko.observable(undefined);

        self.autoscrollEnabled = ko.observable(true);

        self.filters = self.settings.terminalFilters;
        self.filterRegex = ko.observable();

        self.cmdHistory = [];
        self.cmdHistoryIdx = -1;

        self.enableFancyFunctionality = ko.observable(true);
        self.disableTerminalLogDuringPrinting = ko.observable(false);

        self.acceptableFancyTime = 500;
        self.acceptableUnfancyTime = 300;
        self.reenableTimeout = 5000;

        self.forceFancyFunctionality = ko.observable(false);
        self.forceTerminalLogDuringPrinting = ko.observable(false);

        self.fancyFunctionality = ko.pureComputed(function() {
            return self.enableFancyFunctionality() || self.forceFancyFunctionality();
        });
        self.terminalLogDuringPrinting = ko.pureComputed(function() {
            return !self.disableTerminalLogDuringPrinting() || self.forceTerminalLogDuringPrinting();
        });

        self.displayedLines = ko.pureComputed(function() {
            if (!self.enableFancyFunctionality()) {
                return self.log();
            }

            var regex = self.filterRegex();
            var lineVisible = function(entry) {
                return regex == undefined || !entry.line.match(regex);
            };

            var filtered = false;
            var result = [];
            var lines = self.log();
            _.each(lines, function(entry) {
                if (lineVisible(entry)) {
                    result.push(entry);
                    filtered = false;
                } else if (!filtered) {
                    result.push(self._toInternalFormat("[...]", "filtered"));
                    filtered = true;
                }
            });

            return result;
        });

        self.plainLogOutput = ko.pureComputed(function() {
            if (self.fancyFunctionality()) {
                return;
            }
            return self.plainLogLines().join("\n");
        });

        self.lineCount = ko.pureComputed(function() {
            if (!self.fancyFunctionality()) {
                return;
            }

            var regex = self.filterRegex();
            var lineVisible = function(entry) {
                return regex == undefined || !entry.line.match(regex);
            };

            var lines = self.log();
            var total = lines.length;
            var displayed = _.filter(lines, lineVisible).length;
            var filtered = total - displayed;

            if (filtered > 0) {
                if (total > self.upperLimit()) {
                    return _.sprintf(gettext("showing %(displayed)d lines (%(filtered)d of %(total)d total lines filtered, buffer full)"), {displayed: displayed, total: total, filtered: filtered});
                } else {
                    return _.sprintf(gettext("showing %(displayed)d lines (%(filtered)d of %(total)d total lines filtered)"), {displayed: displayed, total: total, filtered: filtered});
                }
            } else {
                if (total > self.upperLimit()) {
                    return _.sprintf(gettext("showing %(displayed)d lines (buffer full)"), {displayed: displayed});
                } else {
                    return _.sprintf(gettext("showing %(displayed)d lines"), {displayed: displayed});
                }
            }
        });

        self.autoscrollEnabled.subscribe(function(newValue) {
            if (newValue) {
                self.log(self.log.slice(-self.buffer()));
            }
        });

        self.activeFilters = ko.observableArray([]);
        self.activeFilters.subscribe(function(e) {
            self.updateFilterRegex();
        });

        self.blacklist=[];
        self.settings.serial_autoUppercaseBlacklist.subscribe(function(newValue) {
            self.blacklist = splitTextToArray(newValue, ",", true);
        });

        self._reenableFancyTimer = undefined;
        self._reenableUnfancyTimer = undefined;
        self._disableFancy = function(difference) {
            log.warn("Terminal: Detected slow client (needed " + difference + "ms for processing new log data), disabling fancy terminal functionality");
            if (self._reenableFancyTimer) {
                window.clearTimeout(self._reenableFancyTimer);
                self._reenableFancyTimer = undefined;
            }
            self.enableFancyFunctionality(false);
        };
        self._reenableFancy = function(difference) {
            if (self._reenableFancyTimer) return;
            self._reenableFancyTimer = window.setTimeout(function() {
                log.info("Terminal: Client speed recovered, enabling fancy terminal functionality");
                self.enableFancyFunctionality(true);
            }, self.reenableTimeout);
        };
        self._disableUnfancy = function(difference) {
            log.warn("Terminal: Detected very slow client (needed " + difference + "ms for processing new log data), completely disabling terminal output during printing");
            if (self._reenableUnfancyTimer) {
                window.clearTimeout(self._reenableUnfancyTimer);
                self._reenableUnfancyTimer = undefined;
            }
            self.disableTerminalLogDuringPrinting(true);
        };
        self._reenableUnfancy = function() {
            if (self._reenableUnfancyTimer) return;
            self._reenableUnfancyTimer = window.setTimeout(function() {
                log.info("Terminal: Client speed recovered, enabling terminal output during printing");
                self.disableTerminalLogDuringPrinting(false);
            }, self.reenableTimeout);
        };

        self.fromCurrentData = function(data) {
            self._processStateData(data.state);

            var start = new Date().getTime();
            self._processCurrentLogData(data.logs);
            var end = new Date().getTime();
            var difference = end - start;

            if (self.enableFancyFunctionality()) {
                // fancy enabled -> check if we need to disable fancy
                if (difference >= self.acceptableFancyTime) {
                    self._disableFancy(difference);
                }
            } else if (!self.disableTerminalLogDuringPrinting()) {
                // fancy disabled, unfancy not -> check if we need to disable unfancy or re-enable fancy
                if (difference >= self.acceptableUnfancyTime) {
                    self._disableUnfancy(difference);
                } else if (difference < self.acceptableFancyTime / 2.0) {
                    self._reenableFancy(difference);
                }
            } else {
                // fancy & unfancy disabled -> check if we need to re-enable unfancy
                if (difference < self.acceptableUnfancyTime / 2.0) {
                    self._reenableUnfancy(difference);
                }
            }
        };

        self.fromHistoryData = function(data) {
            self._processStateData(data.state);
            self._processHistoryLogData(data.logs);
        };

        self._processCurrentLogData = function(data) {
            var length = self.log().length;
            if (length >= self.upperLimit()) {
                return;
            }

            if (!self.terminalLogDuringPrinting() && self.isPrinting()) {
                var last = self.plainLogLines()[self.plainLogLines().length - 1];
                var disabled = "--- client too slow, log output disabled while printing ---";
                if (last != disabled) {
                    self.plainLogLines.push(disabled);
                }
                return;
            }

            var newData = (data.length + length > self.upperLimit())
                ? data.slice(0, self.upperLimit() - length)
                : data;
            if (!newData) {
                return;
            }

            if (!self.fancyFunctionality()) {
                // lite version of the terminal - text output only
                self.plainLogLines(self.plainLogLines().concat(newData).slice(-self.buffer()));
                self.updateOutput();
                return;
            }

            var newLog = self.log().concat(_.map(newData, function(line) { return self._toInternalFormat(line) }));
            if (newData.length != data.length) {
                var cutoff = "--- too many lines to buffer, cut off ---";
                newLog.push(self._toInternalFormat(cutoff, "cut"));
            }

            if (self.autoscrollEnabled()) {
                // we only keep the last <buffer> entries
                newLog = newLog.slice(-self.buffer());
            }
            self.log(newLog);
            self.updateOutput();
        };

        self._processHistoryLogData = function(data) {
            self.plainLogLines(data);
            self.log(_.map(data, function(line) { return self._toInternalFormat(line) }));
            self.updateOutput();
        };

        self._toInternalFormat = function(line, type) {
            if (type == undefined) {
                type = "line";
            }
            return {line: escapeUnprintableCharacters(line), type: type}
        };

        self._processStateData = function(data) {
            self.isErrorOrClosed(data.flags.closedOrError);
            self.isOperational(data.flags.operational);
            self.isPaused(data.flags.paused);
            self.isPrinting(data.flags.printing);
            self.isError(data.flags.error);
            self.isReady(data.flags.ready);
            self.isLoading(data.flags.loading);
        };

        self.updateFilterRegex = function() {
            var filterRegexStr = self.activeFilters().join("|").trim();
            if (filterRegexStr == "") {
                self.filterRegex(undefined);
            } else {
                self.filterRegex(new RegExp(filterRegexStr));
            }
            self.updateOutput();
        };

        self.updateOutput = function() {
            if (self.tabActive && OctoPrint.coreui.browserTabVisible && self.autoscrollEnabled()) {
                self.scrollToEnd();
            }
        };

        self.gotoTerminalCommand = function() {
            // skip if user highlights text.
            var sel = getSelection().toString();
            if (sel) {
                return;
            }

            $("#terminal-command").focus();
        };

        self.toggleAutoscroll = function() {
            self.autoscrollEnabled(!self.autoscrollEnabled());
        };

        self.selectAll = function() {
            var container = self.fancyFunctionality() ? $("#terminal-output") : $("#terminal-output-lowfi");
            if (container.length) {
                container.selectText();
            }
        };

        self.scrollToEnd = function() {
            var container = self.fancyFunctionality() ? $("#terminal-output") : $("#terminal-output-lowfi");
            if (container.length) {
                container.scrollTop(container[0].scrollHeight);
            }
        };

        self.copyAll = function() {
            copyToClipboard(self.plainLogLines().join("\n"));
        };

        // command matching regex
        // (Example output for inputs G0, G1, G28.1, M117 test)
        // - 1: code including optional subcode. Example: G0, G1, G28.1, M117
        // - 2: main code only. Example: G0, G1, G28, M117
        // - 3: sub code, if available. Example: undefined, undefined, .1, undefined
        // - 4: command parameters incl. leading whitespace, if any. Example: "", "", "", " test"
        var commandRe = /^(([gmt][0-9]+)(\.[0-9+])?)(\s.*)?/i;

        self.sendCommand = function() {
            var command = self.command();
            if (!command) {
                return;
            }

            var commandToSend = command;
            var commandMatch = commandToSend.match(commandRe);
            if (commandMatch !== null) {
                var fullCode = commandMatch[1].toUpperCase(); // full code incl. sub code
                var mainCode = commandMatch[2].toUpperCase(); // main code only without sub code

                if (self.blacklist.indexOf(mainCode) < 0 && self.blacklist.indexOf(fullCode) < 0) {
                    // full or main code not on blacklist -> upper case the whole command
                    commandToSend = commandToSend.toUpperCase();
                } else {
                    // full or main code on blacklist -> only upper case that and leave parameters as is
                    commandToSend = fullCode + (commandMatch[4] !== undefined ? commandMatch[4] : "");
                }
            }

            if (commandToSend) {
                OctoPrint.control.sendGcode(commandToSend)
                    .done(function() {
                        self.cmdHistory.push(command);
                        self.cmdHistory.slice(-300); // just to set a sane limit to how many manually entered commands will be saved...
                        self.cmdHistoryIdx = self.cmdHistory.length;
                        self.command("");
                    });
            }
        };

        self.fakeAck = function() {
            OctoPrint.connection.fakeAck();
        };

        self.handleKeyDown = function(event) {
            var keyCode = event.keyCode;

            if (keyCode == 38 || keyCode == 40) {
                if (keyCode == 38 && self.cmdHistory.length > 0 && self.cmdHistoryIdx > 0) {
                    self.cmdHistoryIdx--;
                } else if (keyCode == 40 && self.cmdHistoryIdx < self.cmdHistory.length - 1) {
                    self.cmdHistoryIdx++;
                }

                if (self.cmdHistoryIdx >= 0 && self.cmdHistoryIdx < self.cmdHistory.length) {
                    self.command(self.cmdHistory[self.cmdHistoryIdx]);
                }

                // prevent the cursor from being moved to the beginning of the input field (this is actually the reason
                // why we do the arrow key handling in the keydown event handler, keyup would be too late already to
                // prevent this from happening, causing a jumpy cursor)
                return false;
            }

            // do not prevent default action
            return true;
        };

        self.handleKeyUp = function(event) {
            if (event.keyCode == 13) {
                self.sendCommand();
            }

            // do not prevent default action
            return true;
        };

        self.onAfterTabChange = function(current, previous) {
            self.tabActive = current == "#term";
            self.updateOutput();
        };

    }

    OCTOPRINT_VIEWMODELS.push({
        construct: TerminalViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#term"]
    });
});
