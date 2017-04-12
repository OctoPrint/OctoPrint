function ItemListHelper(listType, supportedSorting, supportedFilters, defaultSorting, defaultFilters, exclusiveFilters, filesPerPage) {
    var self = this;

    self.listType = listType;
    self.supportedSorting = supportedSorting;
    self.supportedFilters = supportedFilters;
    self.defaultSorting = defaultSorting;
    self.defaultFilters = defaultFilters;
    self.exclusiveFilters = exclusiveFilters;

    self.searchFunction = undefined;

    self.allItems = [];
    self.allSize = ko.observable(0);

    self.items = ko.observableArray([]);
    self.pageSize = ko.observable(filesPerPage);
    self.currentPage = ko.observable(0);
    self.currentSorting = ko.observable(self.defaultSorting);
    self.currentFilters = ko.observableArray(self.defaultFilters);
    self.selectedItem = ko.observable(undefined);

    //~~ item handling

    self.refresh = function() {
        self._updateItems();
    };

    self.updateItems = function(items) {
        self.allItems = items;
        self.allSize(items.length);
        self._updateItems();
    };

    self.selectItem = function(matcher) {
        var itemList = self.items();
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                self.selectedItem(itemList[i]);
                break;
            }
        }
    };

    self.selectNone = function() {
        self.selectedItem(undefined);
    };

    self.isSelected = function(data) {
        return self.selectedItem() == data;
    };

    self.isSelectedByMatcher = function(matcher) {
        return matcher(self.selectedItem());
    };

    self.removeItem = function(matcher) {
        var item = self.getItem(matcher, true);
        if (item === undefined) {
            return;
        }

        var index = self.allItems.indexOf(item);
        if (index > -1) {
            self.allItems.splice(index, 1);
            self._updateItems();
        }
    };

    //~~ pagination

    self.paginatedItems = ko.dependentObservable(function() {
        if (self.items() == undefined) {
            return [];
        } else if (self.pageSize() == 0) {
            return self.items();
        } else {
            var from = Math.max(self.currentPage() * self.pageSize(), 0);
            var to = Math.min(from + self.pageSize(), self.items().length);
            return self.items().slice(from, to);
        }
    });
    self.lastPage = ko.dependentObservable(function() {
        return (self.pageSize() == 0 ? 1 : Math.ceil(self.items().length / self.pageSize()) - 1);
    });
    self.pages = ko.dependentObservable(function() {
        var pages = [];
        if (self.pageSize() == 0) {
            pages.push({ number: 0, text: 1 });
        } else if (self.lastPage() < 7) {
            for (var i = 0; i < self.lastPage() + 1; i++) {
                pages.push({ number: i, text: i+1 });
            }
        } else {
            pages.push({ number: 0, text: 1 });
            if (self.currentPage() < 5) {
                for (var i = 1; i < 5; i++) {
                    pages.push({ number: i, text: i+1 });
                }
                pages.push({ number: -1, text: "…"});
            } else if (self.currentPage() > self.lastPage() - 5) {
                pages.push({ number: -1, text: "…"});
                for (var i = self.lastPage() - 4; i < self.lastPage(); i++) {
                    pages.push({ number: i, text: i+1 });
                }
            } else {
                pages.push({ number: -1, text: "…"});
                for (var i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    pages.push({ number: i, text: i+1 });
                }
                pages.push({ number: -1, text: "…"});
            }
            pages.push({ number: self.lastPage(), text: self.lastPage() + 1})
        }
        return pages;
    });

    self.switchToItem = function(matcher) {
        var pos = -1;
        var itemList = self.items();
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                pos = i;
                break;
            }
        }

        if (pos > -1) {
            var page = Math.floor(pos / self.pageSize());
            self.changePage(page);
        }
    };

    self.changePage = function(newPage) {
        if (newPage < 0 || newPage > self.lastPage())
            return;
        self.currentPage(newPage);
    };    self.prevPage = function() {
        if (self.currentPage() > 0) {
            self.currentPage(self.currentPage() - 1);
        }
    };
    self.nextPage = function() {
        if (self.currentPage() < self.lastPage()) {
            self.currentPage(self.currentPage() + 1);
        }
    };

    self.getItem = function(matcher, all) {
        var itemList;
        if (all !== undefined && all === true) {
            itemList = self.allItems;
        } else {
            itemList = self.items();
        }
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                return itemList[i];
            }
        }

        return undefined;
    };

    //~~ searching

    self.changeSearchFunction = function(searchFunction) {
        self.searchFunction = searchFunction;
        self.changePage(0);
        self._updateItems();
    };

    self.resetSearch = function() {
        self.changeSearchFunction(undefined);
    };

    //~~ sorting

    self.changeSorting = function(sorting) {
        if (!_.contains(_.keys(self.supportedSorting), sorting))
            return;

        self.currentSorting(sorting);
        self._saveCurrentSortingToLocalStorage();

        self.changePage(0);
        self._updateItems();
    };

    //~~ filtering

    self.toggleFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        if (_.contains(self.currentFilters(), filter)) {
            self.removeFilter(filter);
        } else {
            self.addFilter(filter);
        }
    };

    self.addFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        for (var i = 0; i < self.exclusiveFilters.length; i++) {
            if (_.contains(self.exclusiveFilters[i], filter)) {
                for (var j = 0; j < self.exclusiveFilters[i].length; j++) {
                    if (self.exclusiveFilters[i][j] == filter)
                        continue;
                    self.removeFilter(self.exclusiveFilters[i][j]);
                }
            }
        }

        var filters = self.currentFilters();
        filters.push(filter);
        self.currentFilters(filters);
        self._saveCurrentFiltersToLocalStorage();

        self.changePage(0);
        self._updateItems();
    };

    self.removeFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        var filters = self.currentFilters();
        filters = _.without(filters, filter);
        self.currentFilters(filters);
        self._saveCurrentFiltersToLocalStorage();

        self.changePage(0);
        self._updateItems();
    };

    //~~ update for sorted and filtered view

    self._updateItems = function() {
        // determine comparator
        var comparator = undefined;
        var currentSorting = self.currentSorting();
        if (typeof currentSorting !== 'undefined' && typeof self.supportedSorting[currentSorting] !== 'undefined') {
            comparator = self.supportedSorting[currentSorting];
        }

        // work on all items
        var result = self.allItems;

        // filter if necessary
        var filters = self.currentFilters();
        _.each(filters, function(filter) {
            if (typeof filter !== 'undefined' && typeof supportedFilters[filter] !== 'undefined')
                result = _.filter(result, supportedFilters[filter]);
        });

        // search if necessary
        if (typeof self.searchFunction !== 'undefined' && self.searchFunction) {
            result = _.filter(result, self.searchFunction);
        }

        // sort if necessary
        if (typeof comparator !== 'undefined')
            result.sort(comparator);

        // set result list
        self.items(result);
    };

    //~~ local storage

    self._saveCurrentSortingToLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            var currentSorting = self.currentSorting();
            if (currentSorting !== undefined)
                localStorage[self.listType + "." + "currentSorting"] = currentSorting;
            else
                localStorage[self.listType + "." + "currentSorting"] = undefined;
        }
    };

    self._loadCurrentSortingFromLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            if (_.contains(_.keys(supportedSorting), localStorage[self.listType + "." + "currentSorting"]))
                self.currentSorting(localStorage[self.listType + "." + "currentSorting"]);
            else
                self.currentSorting(defaultSorting);
        }
    };

    self._saveCurrentFiltersToLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            var filters = _.intersection(_.keys(self.supportedFilters), self.currentFilters());
            localStorage[self.listType + "." + "currentFilters"] = JSON.stringify(filters);
        }
    };

    self._loadCurrentFiltersFromLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            self.currentFilters(_.intersection(_.keys(self.supportedFilters), JSON.parse(localStorage[self.listType + "." + "currentFilters"])));
        }
    };

    self._initializeLocalStorage = function() {
        if (!Modernizr.localstorage)
            return false;

        if (localStorage[self.listType + "." + "currentSorting"] !== undefined && localStorage[self.listType + "." + "currentFilters"] !== undefined && JSON.parse(localStorage[self.listType + "." + "currentFilters"]) instanceof Array)
            return true;

        localStorage[self.listType + "." + "currentSorting"] = self.defaultSorting;
        localStorage[self.listType + "." + "currentFilters"] = JSON.stringify(self.defaultFilters);

        return true;
    };

    self._loadCurrentFiltersFromLocalStorage();
    self._loadCurrentSortingFromLocalStorage();
}

function formatSize(bytes) {
    if (!bytes) return "-";

    var units = ["bytes", "KB", "MB", "GB"];
    for (var i = 0; i < units.length; i++) {
        if (bytes < 1024) {
            return _.sprintf("%3.1f%s", bytes, units[i]);
        }
        bytes /= 1024;
    }
    return _.sprintf("%.1f%s", bytes, "TB");
}

function bytesFromSize(size) {
    if (size == undefined || size.trim() == "") return undefined;

    var parsed = size.match(/^([+]?[0-9]*\.?[0-9]+)(?:\s*)?(.*)$/);
    var number = parsed[1];
    var unit = parsed[2].trim();

    if (unit == "") return parseFloat(number);

    var units = {
        b: 1,
        byte: 1,
        bytes: 1,
        kb: 1024,
        mb: Math.pow(1024, 2),
        gb: Math.pow(1024, 3),
        tb: Math.pow(1024, 4)
    };
    unit = unit.toLowerCase();

    if (!units.hasOwnProperty(unit)) {
        return undefined;
    }

    var factor = units[unit];
    return number * factor;
}

function formatDuration(seconds) {
    if (!seconds) return "-";
    if (seconds < 1) return "00:00:00";

    var s = seconds % 60;
    var m = (seconds % 3600) / 60;
    var h = seconds / 3600;

    return _.sprintf(gettext(/* L10N: duration format */ "%(hour)02d:%(minute)02d:%(second)02d"), {hour: h, minute: m, second: s});
}

function formatFuzzyEstimation(seconds, base) {
    if (!seconds || seconds < 1) return "-";

    var m;
    if (base != undefined) {
        m = moment(base);
    } else {
        m = moment();
    }

    m.add(seconds, "s");
    return m.fromNow(true);
}

function formatFuzzyPrintTime(totalSeconds) {
    /**
     * Formats a print time estimate in a very fuzzy way.
     *
     * Accuracy decreases the higher the estimation is:
     *
     *   * less than 30s: "a couple of seconds"
     *   * 30s to a minute: "less than a minute"
     *   * 1 to 30min: rounded to full minutes, above 30s is minute + 1 ("27 minutes", "2 minutes")
     *   * 30min to 40min: "40 minutes"
     *   * 40min to 50min: "50 minutes"
     *   * 50min to 1h: "1 hour"
     *   * 1 to 12h: rounded to half hours, 15min to 45min is ".5", above that hour + 1 ("4 hours", "2.5 hours")
     *   * 12 to 24h: rounded to full hours, above 30min is hour + 1, over 23.5h is "1 day"
     *   * Over a day: rounded to half days, 8h to 16h is ".5", above that days + 1 ("1 day", "4 days", "2.5 days")
     */

    if (!totalSeconds || totalSeconds < 1) return "-";

    var d = moment.duration(totalSeconds, "seconds");

    var seconds = d.seconds();
    var minutes = d.minutes();
    var hours = d.hours();
    var days = d.asDays();

    var replacements = {
        days: days,
        hours: hours,
        minutes: minutes,
        seconds: seconds,
        totalSeconds: totalSeconds
    };

    var text = "-";

    if (days >= 1) {
        // days
        if (hours >= 16) {
            replacements.days += 1;
            text = gettext("%(days)d days");
        } else if (hours >= 8 && hours < 16) {
            text = gettext("%(days)d.5 days");
        } else {
            if (days == 1) {
                text = gettext("%(days)d day");
            } else {
                text = gettext("%(days)d days");
            }
        }
    } else if (hours >= 1) {
        // only hours
        if (hours < 12) {
            if (minutes < 15) {
                // less than .15 => .0
                if (hours == 1) {
                    text = gettext("%(hours)d hour");
                } else {
                    text = gettext("%(hours)d hours");
                }
            } else if (minutes >= 15 && minutes < 45) {
                // between .25 and .75 => .5
                text = gettext("%(hours)d.5 hours");
            } else {
                // over .75 => hours + 1
                replacements.hours += 1;
                text = gettext("%(hours)d hours");
            }
        } else {
            if (hours == 23 && minutes > 30) {
                // over 23.5 hours => 1 day
                text = gettext("1 day");
            } else {
                if (minutes > 30) {
                    // over .5 => hours + 1
                    replacements.hours += 1;
                }
                text = gettext("%(hours)d hours");
            }
        }
    } else if (minutes >= 1) {
        // only minutes
        if (minutes < 2) {
            if (seconds < 30) {
                text = gettext("a minute");
            } else {
                text = gettext("2 minutes");
            }
        } else if (minutes < 30) {
            if (seconds > 30) {
                replacements.minutes += 1;
            }
            text = gettext("%(minutes)d minutes");
        } else if (minutes <= 40) {
            text = gettext("40 minutes");
        } else if (minutes <= 50) {
            text = gettext("50 minutes");
        } else {
            text = gettext("1 hour");
        }
    } else {
        // only seconds
        if (seconds < 30) {
            text = gettext("a couple of seconds");
        } else {
            text = gettext("less than a minute");
        }
    }

    return _.sprintf(text, replacements);
}

function formatDate(unixTimestamp) {
    if (!unixTimestamp) return "-";
    return moment.unix(unixTimestamp).format(gettext(/* L10N: Date format */ "YYYY-MM-DD HH:mm"));
}

function formatTimeAgo(unixTimestamp) {
    if (!unixTimestamp) return "-";
    return moment.unix(unixTimestamp).fromNow();
}

function formatFilament(filament) {
    if (!filament || !filament["length"]) return "-";
    var result = "%(length).02fm";
    if (filament.hasOwnProperty("volume") && filament.volume) {
        result += " / " + "%(volume).02fcm³";
    }
    return _.sprintf(result, {length: filament["length"] / 1000, volume: filament["volume"]});
}

function cleanTemperature(temp) {
    if (!temp || temp < 10) return gettext("off");
    return temp;
}

function formatTemperature(temp, showF) {
    if (!temp || temp < 10) return gettext("off");
    if (showF) {
        return _.sprintf("%.1f&deg;C (%.1f&deg;F)", temp, temp * 9 / 5 + 32);
    } else {
        return _.sprintf("%.1f&deg;C", temp);
    }
}

function pnotifyAdditionalInfo(inner) {
    return '<div class="pnotify_additional_info">'
        + '<div class="pnotify_more"><a href="#" onclick="$(this).children().toggleClass(\'icon-caret-right icon-caret-down\').parent().parent().next().slideToggle(\'fast\')">More <i class="icon-caret-right"></i></a></div>'
        + '<div class="pnotify_more_container hide">' + inner + '</div>'
        + '</div>';
}

function ping(url, callback) {
    var img = new Image();
    var calledBack = false;

    img.onload = function() {
        callback(true);
        calledBack = true;
    };
    img.onerror = function() {
        if (!calledBack) {
            callback(true);
            calledBack = true;
        }
    };
    img.src = url;
    setTimeout(function() {
        if (!calledBack) {
            callback(false);
            calledBack = true;
        }
    }, 1500);
}

function showOfflineOverlay(title, message, reconnectCallback) {
    if (title == undefined) {
        title = gettext("Server is offline");
    }

    $("#offline_overlay_title").text(title);
    $("#offline_overlay_message").html(message);
    $("#offline_overlay_reconnect").click(reconnectCallback);
    if (!$("#offline_overlay").is(":visible"))
        $("#offline_overlay").show();
}

function hideOfflineOverlay() {
    $("#offline_overlay").hide();
}

function showMessageDialog(msg, options) {
    options = options || {};
    if (_.isPlainObject(msg)) {
        options = msg;
    } else {
        options.message = msg;
    }

    var title = options.title || "";
    var message = options.message || "";
    var close = options.close || gettext("Close");
    var onclose = options.onclose || undefined;
    var onshow = options.onshow || undefined;
    var onshown = options.onshown || undefined;

    if (_.isString(message)) {
        message = $("<p>" + message + "</p>");
    }

    var modalHeader = $('<a href="javascript:void(0)" class="close" data-dismiss="modal" aria-hidden="true">&times;</a><h3>' + title + '</h3>');
    var modalBody = $(message);
    var modalFooter = $('<a href="javascript:void(0)" class="btn" data-dismiss="modal" aria-hidden="true">' + close + '</a>');

    var modal = $('<div></div>')
        .addClass('modal hide fade')
        .append($('<div></div>').addClass('modal-header').append(modalHeader))
        .append($('<div></div>').addClass('modal-body').append(modalBody))
        .append($('<div></div>').addClass('modal-footer').append(modalFooter));

    modal.on("hidden", function() {
        if (onclose && _.isFunction(onclose)) {
            onclose();
        }
    });

    if (onshow) {
        modal.on("show", onshow);
    }

    if (onshown) {
        modal.on("shown", onshown);
    }

    modal.modal("show");
    return modal;
}

function showConfirmationDialog(msg, onacknowledge, options) {
    options = options || {};
    if (_.isPlainObject(msg)) {
        options = msg;
    } else {
        options.message = msg;
        options.onproceed = onacknowledge;
    }

    var title = options.title || gettext("Are you sure?");
    var message = options.message || "";
    var question = options.question || gettext("Are you sure you want to proceed?");
    var cancel = options.cancel || gettext("Cancel");
    var proceed = options.proceed || gettext("Proceed");
    var proceedClass = options.proceedClass || "danger";
    var onproceed = options.onproceed || undefined;
    var dialogClass = options.dialogClass || "";

    var modalHeader = $('<a href="javascript:void(0)" class="close" data-dismiss="modal" aria-hidden="true">&times;</a><h3>' + title + '</h3>');
    var modalBody = $('<p>' + message + '</p><p>' + question + '</p>');

    var cancelButton = $('<a href="javascript:void(0)" class="btn">' + cancel + '</a>')
        .attr("data-dismiss", "modal")
        .attr("aria-hidden", "true");
    var proceedButton = $('<a href="javascript:void(0)" class="btn">' + proceed + '</a>')
        .addClass("btn-" + proceedClass);

    var modal = $('<div></div>')
        .addClass('modal hide fade')
        .addClass(dialogClass)
        .append($('<div></div>').addClass('modal-header').append(modalHeader))
        .append($('<div></div>').addClass('modal-body').append(modalBody))
        .append($('<div></div>').addClass('modal-footer').append(cancelButton).append(proceedButton));
    modal.modal("show");

    proceedButton.click(function(e) {
        e.preventDefault();
        modal.modal("hide");
        if (onproceed && _.isFunction(onproceed)) {
            onproceed(e);
        }
    });

    return modal;
}

function showReloadOverlay() {
    $("#reloadui_overlay").show();
}

function commentableLinesToArray(lines) {
    return splitTextToArray(lines, "\n", true, function(item) {return !_.startsWith(item, "#")});
}

function splitTextToArray(text, sep, stripEmpty, filter) {
    return _.filter(
        _.map(
            text.split(sep),
            function(item) { return (item) ? item.trim() : ""; }
        ),
        function(item) { return (stripEmpty ? item : true) && (filter ? filter(item) : true); }
    );
}

/**
 * Returns true if comparing data and oldData yields changes, false otherwise.
 *
 * E.g.
 *
 *   hasDataChanged(
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "three", key: "value"}},
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "3", four: "4"}}
 *   )
 *
 * will return
 *
 *   true
 *
 * and
 *
 *   hasDataChanged(
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "3"}},
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "3"}}
 *   )
 *
 * will return
 *
 *   false
 *
 * Note that this will assume data and oldData to be structurally identical (same keys)
 * and is optimized to check for value changes, not key updates.
 */
function hasDataChanged(data, oldData) {
    if (data == undefined) {
        return false;
    }

    if (oldData == undefined) {
        return true;
    }

    if (_.isPlainObject(data)) {
        return _.any(_.keys(data), function(key) {return hasDataChanged(data[key], oldData[key]);});
    } else {
        return !_.isEqual(data, oldData);
    }
}

/**
 * Compare provided data and oldData plain objects and only return those
 * substructures of data that actually changed.
 *
 * E.g.
 *
 *   getOnlyChangedData(
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "three"}},
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "3"}}
 *   )
 *
 * will return
 *
 *   {fnord: {three: "three"}}
 *
 * and
 *
 *   getOnlyChangedData(
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "3"}},
 *     {foo: "bar", fnord: {one: "1", two: "2", three: "3"}}
 *   )
 *
 * will return
 *
 *   {}
 *
 * Note that this will assume data and oldData to be structurally identical (same keys)
 * and is optimized to check for value changes, not key updates.
 */
function getOnlyChangedData(data, oldData) {
    if (data == undefined) {
        return {};
    }

    if (oldData == undefined) {
        return data;
    }

    var f = function(root, oldRoot) {
        if (!_.isPlainObject(root)) {
            return root;
        }

        var retval = {};
        _.forOwn(root, function(value, key) {
            var oldValue = undefined;
            if (oldRoot != undefined && oldRoot.hasOwnProperty(key)) {
                oldValue = oldRoot[key];
            }
            if (_.isPlainObject(value)) {
                if (oldValue == undefined) {
                    retval[key] = value;
                } else if (hasDataChanged(value, oldValue)) {
                    retval[key] = f(value, oldValue);
                }
            } else {
                if (!_.isEqual(value, oldValue)) {
                    retval[key] = value;
                }
            }
        });
        return retval;
    };

    return f(data, oldData);
}

function callViewModels(allViewModels, method, callback) {
    callViewModelsIf(allViewModels, method, undefined, callback);
}

function callViewModelsIf(allViewModels, method, condition, callback) {
    if (condition == undefined || !_.isFunction(condition)) {
        condition = function() { return true; };
    }

    var parameters = undefined;
    if (!_.isFunction(callback)) {
        // if callback is not a function that means we are supposed to directly
        // call the view model method instead of providing it to the callback
        // - let's figure out how

        if (callback == undefined) {
            // directly call view model method with no parameters
            parameters = undefined;
            log.trace("Calling method", method, "on view models");
        } else if (_.isArray(callback)) {
            // directly call view model method with these parameters
            parameters = callback;
            log.trace("Calling method", method, "on view models with specified parameters", parameters);
        } else {
            // ok, this doesn't make sense, callback is neither undefined nor
            // an array, we'll return without doing anything
            return;
        }

        // we reset this here so we now further down that we want to call
        // the method directly
        callback = undefined;
    } else {
        log.trace("Providing method", method, "on view models to specified callback", callback);
    }

    _.each(allViewModels, function(viewModel) {
        if (viewModel.hasOwnProperty(method) && condition(viewModel, method)) {
            try {
                if (callback == undefined) {
                    if (parameters != undefined) {
                        // call the method with the provided parameters
                        viewModel[method].apply(viewModel, parameters);
                    } else {
                        // call the method without parameters
                        viewModel[method]();
                    }
                } else {
                    // provide the method to the callback
                    callback(viewModel[method], viewModel);
                }
            } catch (exc) {
                log.error("Error calling", method, "on view model", viewModel.constructor.name, ":", (exc.stack || exc));
            }
        }
    });
}

var sizeObservable = function(observable) {
    return ko.computed({
        read: function() {
            return formatSize(observable());
        },
        write: function(value) {
            var result = bytesFromSize(value);
            if (result != undefined) {
                observable(result);
            }
        }
    })
};

var getQueryParameterByName = function(name, url) {
    // from http://stackoverflow.com/a/901144/2028598
    if (!url) {
      url = window.location.href;
    }
    name = name.replace(/[\[\]]/g, "\\$&");
    var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
        results = regex.exec(url);
    if (!results) return null;
    if (!results[2]) return '';
    return decodeURIComponent(results[2].replace(/\+/g, " "));
};

/**
 * Escapes unprintable ASCII characters in the provided string.
 *
 * E.g. turns a null byte in the string into "\x00".
 *
 * Only characters 0 to 31, 127 and 255 will be escaped, that
 * should leave printable characters and unicode alone.
 *
 * Originally based on
 * https://gist.github.com/mathiasbynens/1243213#gistcomment-53590
 *
 * @param str The string to escape
 * @returns {string}
 */
var escapeUnprintableCharacters = function(str) {
    var result = "";
    var index = 0;
    var charCode;

    while (!isNaN(charCode = str.charCodeAt(index))) {
        if (charCode < 32 || charCode == 127 || charCode == 255) {
            // special hex chars
            result += "\\x" + (charCode > 15 ? "" : "0") + charCode.toString(16)
        } else {
            // anything else
            result += str[index];
        }

        index++;
    }
    return result;
};
