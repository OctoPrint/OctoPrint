$(function () {
    function AchievementsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.access = parameters[1];

        self.stats = undefined;
        self.statsFetched = ko.observable(false);
        self.dummy = ko.observable();

        self.collectingSince = ko.pureComputed(() => {
            self.dummy();
            if (!self.statsFetched()) {
                return "n/a";
            }

            return `${formatDate(self.stats.created())} (${formatTimeAgo(
                self.stats.created()
            )})`;
        });

        self.collectionVersion = ko.pureComputed(() => {
            if (!self.statsFetched()) {
                return "n/a";
            }
            return `OctoPrint ${self.stats.created_version()}`;
        });

        self.prints = ko.pureComputed(() => {
            if (!self.statsFetched()) {
                return "n/a";
            }
            if (self.stats.prints_started() === 0) {
                return gettext("No prints yet");
            }
            return _.sprintf(gettext("%(prints)s (%(finished)s finished)"), {
                prints: this.stats.prints_started(),
                finished: self.stats.prints_finished()
            });
        });

        self.duration = ko.pureComputed(() => {
            if (!self.statsFetched()) {
                return "n/a";
            }
            return _.sprintf(gettext("%(total)s (%(finished)s finished)"), {
                total: formatDuration(self.stats.print_duration_total()),
                finished: formatDuration(self.stats.print_duration_finished())
            });
        });

        self.longestPrint = ko.pureComputed(() => {
            self.dummy();
            if (!self.statsFetched()) {
                return "n/a";
            }
            return _.sprintf(
                gettext("%(duration)s (finished on %(date)s, %(timeSince)s)"),
                {
                    duration: formatDuration(self.stats.longest_print_duration()),
                    date: formatDate(self.stats.longest_print_date()),
                    timeSince: formatTimeAgo(self.stats.longest_print_date())
                }
            );
        });

        self.requestData = () => {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACHIEVEMENTS_VIEW
                )
            ) {
                return;
            }
            OctoPrint.plugins.achievements.get().done(self.fromResponse);
        };

        self.fromResponse = (response) => {
            self.fromStatsResponse(response.stats);
        };

        self.fromStatsResponse = (response) => {
            if (self.stats === undefined) {
                self.stats = ko.mapping.fromJS(response);
                self.statsFetched(true);
            } else {
                ko.mapping.fromJS(response, self.stats);
            }
        };

        self.onServerReconnect = self.onUserLoggedIn = () => {
            if (
                !self.loginState.hasPermission(
                    self.access.permissions.PLUGIN_ACHIEVEMENTS_VIEW
                )
            ) {
                return;
            }
            self.requestData();
        };

        self.onAboutShown = () => {
            self.dummy.notifySubscribers();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AchievementsViewModel,
        dependencies: ["loginStateViewModel", "accessViewModel"],
        elements: ["#about_plugin_achievements"]
    });
});
