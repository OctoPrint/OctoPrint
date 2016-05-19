$(function() {
    function AnnouncementsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];

        self.channels = new ItemListHelper(
            "plugin.announcements.channels",
            {
                "channel": function (a, b) {
                    // sorts ascending
                    if (a["channel"].toLocaleLowerCase() < b["channel"].toLocaleLowerCase()) return -1;
                    if (a["channel"].toLocaleLowerCase() > b["channel"].toLocaleLowerCase()) return 1;
                    return 0;
                }
            },
            {
            },
            "name",
            [],
            [],
            5
        );

        self.unread = ko.observable();
        self.hiddenChannels = [];
        self.channelNotifications = {};

        self.announcementDialog = undefined;
        self.announcementDialogContent = undefined;
        self.announcementDialogTabs = undefined;

        self.setupTabLink = function(item) {
            $("a[data-toggle='tab']", item).on("show", self.resetContentScroll);
        };

        self.resetContentScroll = function() {
            self.announcementDialogContent.scrollTop(0);
        };

        self.toggleButtonCss = function(data) {
            var icon = data.enabled ? "icon-circle" : "icon-circle-blank";
            var disabled = (self.enableToggle(data)) ? "" : " disabled";

            return icon + disabled;
        };

        self.toggleButtonTitle = function(data) {
            return data.forced ? gettext("Cannot be toggled") : (data.enabled ? gettext("Disable Channel") : gettext("Enable Channel"));
        };

        self.enableToggle = function(data) {
            return !data.forced;
        };

        self.markRead = function(channel, until) {
            if (!self.loginState.isAdmin()) return;

            var url = PLUGIN_BASEURL + "announcements/channels/" + channel;

            var payload = {
                command: "read",
                until: until
            };

            $.ajax({
                url: url,
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    self.retrieveData()
                }
            })
        };

        self.toggleChannel = function(channel) {
            if (!self.loginState.isAdmin()) return;

            var url = PLUGIN_BASEURL + "announcements/channels/" + channel;

            var payload = {
                command: "toggle"
            };

            $.ajax({
                url: url,
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function() {
                    self.retrieveData()
                }
            })
        };

        self.refreshAnnouncements = function() {
            self.retrieveData(true);
        };

        self.retrieveData = function(force) {
            if (!self.loginState.isAdmin()) return;

            var url = PLUGIN_BASEURL + "announcements/channels";
            if (force) {
                url += "?force=true";
            }

            $.ajax({
                url: url,
                type: "GET",
                dataType: "json",
                success: function(data) {
                    self.fromResponse(data);
                }
            });
        };

        self.fromResponse = function(data) {
            var currentTab = $("li.active a", self.announcementDialogTabs).attr("href");

            var unread = 0;
            var channels = [];
            _.each(data, function(value, key) {
                value.key = key;
                value.last = value.data.length ? value.data[0].published : undefined;
                value.count = value.data.length;
                unread += value.unread;
                channels.push(value);
            });
            self.channels.updateItems(channels);
            self.unread(unread);

            self.displayAnnouncements(channels);

            self.selectTab(currentTab);
        };

        self.showAnnouncementDialog = function(channel) {
            self.announcementDialogContent.scrollTop(0);

            if (!self.announcementDialog.hasClass("in")) {
                self.announcementDialog.modal({
                    minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
                }).css({
                    width: 'auto',
                    'margin-left': function() { return -($(this).width() /2); }
                });
            }

            var tab = undefined;
            if (channel) {
                tab = "#plugin_announcements_dialog_channel_" + channel;
            }
            self.selectTab(tab);

            return false;
        };

        self.selectTab = function(tab) {
            if (tab != undefined) {
                if (!_.startsWith(tab, "#")) {
                    tab = "#" + tab;
                }
                $('a[href="' + tab + '"]', self.announcementDialogTabs).tab("show");
            } else {
                $('a:first', self.announcementDialogTabs).tab("show");
            }
        };

        self.displayAnnouncements = function(channels) {
            var displayLimit = self.settings.settings.plugins.announcements.display_limit();
            var maxLength = self.settings.settings.plugins.announcements.summary_limit();

            var cutAfterNewline = function(text) {
                text = text.trim();

                var firstNewlinePos = text.indexOf("\n");
                if (firstNewlinePos > 0) {
                    text = text.substr(0, firstNewlinePos).trim();
                }

                return text;
            };

            var stripParagraphs = function(text) {
                if (_.startsWith(text, "<p>")) {
                    text = text.substr("<p>".length);
                }
                if (_.endsWith(text, "</p>")) {
                    text = text.substr(0, text.length - "</p>".length);
                }

                return text.replace(/<\/p>\s*<p>/ig, "<br>");
            };

            _.each(channels, function(value) {
                var key = value.key;
                var channel = value.channel;
                var priority = value.priority;
                var items = value.data;

                if ($.inArray(key, self.hiddenChannels) > -1) {
                    // channel currently ignored
                    return;
                }

                var newItems = _.filter(items, function(entry) { return !entry.read; });
                if (newItems.length == 0) {
                    // no new items at all, we don't display anything for this channel
                    return;
                }

                var displayedItems;
                if (newItems.length > displayLimit) {
                    displayedItems = newItems.slice(0, displayLimit);
                } else {
                    displayedItems = newItems;
                }
                var rest = newItems.length - displayedItems.length;

                var text = "<ul>";
                _.each(displayedItems, function(item) {
                    var limitedSummary = stripParagraphs(item.summary_without_images.trim());
                    if (limitedSummary.length > maxLength) {
                        limitedSummary = limitedSummary.substr(0, maxLength);
                        limitedSummary = limitedSummary.substr(0, Math.min(limitedSummary.length, limitedSummary.lastIndexOf(" ")));
                        limitedSummary += "...";
                    }

                    text += "<li><a href='" + item.link + "' target='_blank' rel='noreferrer noopener'>" + cutAfterNewline(item.title) + "</a><br><small>" + formatTimeAgo(item.published) + "</small><p>" + limitedSummary + "</p></li>";
                });
                text += "</ul>";

                if (rest) {
                    text += gettext(_.sprintf("... and %(rest)d more.", {rest: rest}));
                }

                var options = {
                    title: channel,
                    text: text,
                    hide: false,
                    confirm: {
                        confirm: true,
                        buttons: [{
                            text: gettext("Later"),
                            click: function(notice) {
                                self.hiddenChannels.push(key);
                                notice.remove();
                            }
                        }, {
                            text: gettext("Mark read"),
                            click: function(notice) {
                                self.markRead(key, value.last);
                                notice.remove();
                            }
                        }, {
                            text: gettext("Read..."),
                            addClass: "btn-primary",
                            click: function(notice) {
                                self.showAnnouncementDialog(key);
                                self.markRead(key, value.last);
                                notice.remove();
                            }
                        }]
                    },
                    buttons: {
                        sticker: false,
                        closer: false
                    }
                };

                if (priority == 1) {
                    options.type = "error";
                }

                if (self.channelNotifications[key]) {
                    self.channelNotifications[key].remove();
                }
                self.channelNotifications[key] = new PNotify(options);
            });
        };

        self.onUserLoggedIn = function() {
            self.retrieveData();
        };

        self.onStartup = function() {
            self.announcementDialog = $("#plugin_announcements_dialog");
            self.announcementDialogContent = $("#plugin_announcements_dialog_content");
            self.announcementDialogTabs = $("#plugin_announcements_dialog_tabs");
        }
    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([
        AnnouncementsViewModel,
        ["loginStateViewModel", "settingsViewModel"],
        ["#plugin_announcements_dialog", "#settings_plugin_announcements", "#navbar_plugin_announcements"]
    ]);
});
