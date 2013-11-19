function ItemListHelper(listType, supportedSorting, supportedFilters, defaultSorting, defaultFilters, exclusiveFilters, filesPerPage) {
    var self = this;

    self.listType = listType;
    self.supportedSorting = supportedSorting;
    self.supportedFilters = supportedFilters;
    self.defaultSorting = defaultSorting;
    self.defaultFilters = defaultFilters;
    self.exclusiveFilters = exclusiveFilters;

    self.allItems = [];

    self.items = ko.observableArray([]);
    self.pageSize = ko.observable(filesPerPage);
    self.currentPage = ko.observable(0);
    self.currentSorting = ko.observable(self.defaultSorting);
    self.currentFilters = ko.observableArray(self.defaultFilters);
    self.selectedItem = ko.observable(undefined);

    //~~ item handling

    self.refresh = function() {
        self._updateItems();
    }

    self.updateItems = function(items) {
        self.allItems = items;
        self._updateItems();
    }

    self.selectItem = function(matcher) {
        var itemList = self.items();
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                self.selectedItem(itemList[i]);
                break;
            }
        }
    }

    self.selectNone = function() {
        self.selectedItem(undefined);
    }

    self.isSelected = function(data) {
        return self.selectedItem() == data;
    }

    self.isSelectedByMatcher = function(matcher) {
        return matcher(self.selectedItem());
    }

    //~~ pagination

    self.paginatedItems = ko.dependentObservable(function() {
        if (self.items() == undefined) {
            return [];
        } else {
            var from = Math.max(self.currentPage() * self.pageSize(), 0);
            var to = Math.min(from + self.pageSize(), self.items().length);
            return self.items().slice(from, to);
        }
    })
    self.lastPage = ko.dependentObservable(function() {
        return Math.ceil(self.items().length / self.pageSize()) - 1;
    })
    self.pages = ko.dependentObservable(function() {
        var pages = [];
        if (self.lastPage() < 7) {
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
    })

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
    }

    self.changePage = function(newPage) {
        if (newPage < 0 || newPage > self.lastPage())
            return;
        self.currentPage(newPage);
    }
    self.prevPage = function() {
        if (self.currentPage() > 0) {
            self.currentPage(self.currentPage() - 1);
        }
    }
    self.nextPage = function() {
        if (self.currentPage() < self.lastPage()) {
            self.currentPage(self.currentPage() + 1);
        }
    }

    self.getItem = function(matcher) {
        var itemList = self.items();
        for (var i = 0; i < itemList.length; i++) {
            if (matcher(itemList[i])) {
                return itemList[i];
            }
        }

        return undefined;
    }

    //~~ sorting

    self.changeSorting = function(sorting) {
        if (!_.contains(_.keys(self.supportedSorting), sorting))
            return;

        self.currentSorting(sorting);
        self._saveCurrentSortingToLocalStorage();

        self.changePage(0);
        self._updateItems();
    }

    //~~ filtering

    self.toggleFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        if (_.contains(self.currentFilters(), filter)) {
            self.removeFilter(filter);
        } else {
            self.addFilter(filter);
        }
    }

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
    }

    self.removeFilter = function(filter) {
        if (!_.contains(_.keys(self.supportedFilters), filter))
            return;

        var filters = self.currentFilters();
        filters.pop(filter);
        self.currentFilters(filters);
        self._saveCurrentFiltersToLocalStorage();

        self.changePage(0);
        self._updateItems();
    }

    //~~ update for sorted and filtered view

    self._updateItems = function() {
        // determine comparator
        var comparator = undefined;
        var currentSorting = self.currentSorting();
        if (typeof currentSorting !== undefined && typeof self.supportedSorting[currentSorting] !== undefined) {
            comparator = self.supportedSorting[currentSorting];
        }

        // work on all items
        var result = self.allItems;

        // filter if necessary
        var filters = self.currentFilters();
        _.each(filters, function(filter) {
            if (typeof filter !== undefined && typeof supportedFilters[filter] !== undefined)
                result = _.filter(result, supportedFilters[filter]);
        });

        // sort if necessary
        if (typeof comparator !== undefined)
            result.sort(comparator);

        // set result list
        self.items(result);
    }

    //~~ local storage

    self._saveCurrentSortingToLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            var currentSorting = self.currentSorting();
            if (currentSorting !== undefined)
                localStorage[self.listType + "." + "currentSorting"] = currentSorting;
            else
                localStorage[self.listType + "." + "currentSorting"] = undefined;
        }
    }

    self._loadCurrentSortingFromLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            if (_.contains(_.keys(supportedSorting), localStorage[self.listType + "." + "currentSorting"]))
                self.currentSorting(localStorage[self.listType + "." + "currentSorting"]);
            else
                self.currentSorting(defaultSorting);
        }
    }

    self._saveCurrentFiltersToLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            var filters = _.intersection(_.keys(self.supportedFilters), self.currentFilters());
            localStorage[self.listType + "." + "currentFilters"] = JSON.stringify(filters);
        }
    }

    self._loadCurrentFiltersFromLocalStorage = function() {
        if ( self._initializeLocalStorage() ) {
            self.currentFilters(_.intersection(_.keys(self.supportedFilters), JSON.parse(localStorage[self.listType + "." + "currentFilters"])));
        }
    }

    self._initializeLocalStorage = function() {
        if (!Modernizr.localstorage)
            return false;

        if (localStorage[self.listType + "." + "currentSorting"] !== undefined && localStorage[self.listType + "." + "currentFilters"] !== undefined && JSON.parse(localStorage[self.listType + "." + "currentFilters"]) instanceof Array)
            return true;

        localStorage[self.listType + "." + "currentSorting"] = self.defaultSorting;
        localStorage[self.listType + "." + "currentFilters"] = JSON.stringify(self.defaultFilters);

        return true;
    }

    self._loadCurrentFiltersFromLocalStorage();
    self._loadCurrentSortingFromLocalStorage();
}
