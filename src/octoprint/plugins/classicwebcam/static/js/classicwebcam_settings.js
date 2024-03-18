$(function () {
    function ClassicWebcamSettingsViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self._subscriptions = [];

        self.webRtcServersToText = function (list) {
            self.streamWebrtcIceServersText(self.streamWebrtcIceServers().join(", "));
        };

        self.textToWebRtcServers = function (list) {
            self.streamWebrtcIceServers(
                splitTextToArray(self.streamWebrtcIceServersText(), ",", true)
            );
        };

        self.onBeforeBinding = function () {
            self.snapshotUrl = self.settings.settings.plugins.classicwebcam.snapshot;
            self.snapshotTimeout =
                self.settings.settings.plugins.classicwebcam.snapshotTimeout;
            self.snapshotSslValidation =
                self.settings.settings.plugins.classicwebcam.snapshotSslValidation;
            self.flipH = self.settings.settings.plugins.classicwebcam.flipH;
            self.flipV = self.settings.settings.plugins.classicwebcam.flipV;
            self.rotate90 = self.settings.settings.plugins.classicwebcam.rotate90;
            self.streamUrl = self.settings.settings.plugins.classicwebcam.stream;
            self.webcamEnabled = self.settings.settings.webcam.webcamEnabled;
            self.streamRatio = self.settings.settings.plugins.classicwebcam.streamRatio;
            self.streamTimeout =
                self.settings.settings.plugins.classicwebcam.streamTimeout;
            self.streamWebrtcIceServers =
                self.settings.settings.plugins.classicwebcam.streamWebrtcIceServers;
            self.streamWebrtcIceServersText = ko.observable("");
            self.cacheBuster = self.settings.settings.plugins.classicwebcam.cacheBuster;
            self.available_ratios = ["16:9", "4:3"];

            self.webRtcServersToText();
            self.streamWebrtcIceServers.subscribe(function (value) {
                self.webRtcServersToText();
            });
        };

        self.onSettingsBeforeSave = function () {
            self.textToWebRtcServers();
        };

        self.onUserSettingsHidden = function () {
            self.webRtcServersToText();
        };

        self.streamUrlEscaped = ko.pureComputed(function () {
            return encodeURI(self.streamUrl());
        });

        self.streamType = ko.pureComputed(function () {
            try {
                return determineWebcamStreamType(self.streamUrlEscaped());
            } catch (e) {
                return "";
            }
        });

        self.streamValid = ko.pureComputed(function () {
            var url = self.streamUrlEscaped();
            return !url || validateWebcamUrl(url);
        });

        self.testWebcamStreamUrlBusy = ko.observable(false);
        self.testWebcamStreamUrl = function () {
            var url = self.streamUrlEscaped();
            if (!url) {
                return;
            }

            if (self.testWebcamStreamUrlBusy()) {
                return;
            }

            var text = gettext(
                "If you see your webcam stream below, the entered stream URL is ok."
            );

            var streamType;
            try {
                streamType = self.streamType();
            } catch (e) {
                streamType = "";
            }

            var webcam_element;
            var webrtc_peer_connection;
            if (streamType === "mjpg") {
                webcam_element = $('<img src="' + url + '">');
            } else if (streamType === "hls") {
                webcam_element = $(
                    '<video id="webcam_hls" muted autoplay style="width: 100%"/>'
                );
                video_element = webcam_element[0];
                if (video_element.canPlayType("application/vnd.apple.mpegurl")) {
                    video_element.src = url;
                } else if (Hls.isSupported()) {
                    var hls = new Hls();
                    hls.loadSource(url);
                    hls.attachMedia(video_element);
                }
            } else if (isWebRTCAvailable() && streamType === "webrtc") {
                webcam_element = $(
                    '<video id="webcam_webrtc" muted autoplay playsinline controls style="width: 100%"/>'
                );
                video_element = webcam_element[0];

                webrtc_peer_connection = startWebRTC(
                    video_element,
                    url,
                    self.streamWebrtcIceServers()
                );
            } else {
                throw "Unknown stream type " + streamType;
            }

            var message = $("<div id='webcamTestContainer'></div>")
                .append($("<p></p>"))
                .append(text)
                .append(webcam_element);

            self.testWebcamStreamUrlBusy(true);
            showMessageDialog({
                title: gettext("Stream test"),
                message: message,
                onclose: function () {
                    self.testWebcamStreamUrlBusy(false);
                    if (webrtc_peer_connection != null) {
                        webrtc_peer_connection.close();
                        webrtc_peer_connection = null;
                    }
                }
            });
        };

        self.testWebcamSnapshotUrlBusy = ko.observable(false);
        self.testWebcamSnapshotUrl = function (viewModel, event) {
            if (!self.snapshotUrl()) {
                return;
            }

            if (self.testWebcamSnapshotUrlBusy()) {
                return;
            }

            var errorText = gettext(
                "Could not retrieve snapshot URL, please double check the URL"
            );
            var errorTitle = gettext("Snapshot test failed");

            self.testWebcamSnapshotUrlBusy(true);
            OctoPrint.util
                .testUrl(self.snapshotUrl(), {
                    method: "GET",
                    response: "bytes",
                    timeout: self.settings.settings.webcam.snapshotTimeout(),
                    validSsl: self.settings.settings.webcam.snapshotSslValidation(),
                    content_type_whitelist: ["image/*"],
                    content_type_guess: true
                })
                .done(function (response) {
                    if (!response.result) {
                        if (
                            response.status &&
                            response.response &&
                            response.response.content_type
                        ) {
                            // we could contact the server, but something else was wrong, probably the mime type
                            errorText = gettext(
                                "Could retrieve the snapshot URL, but it didn't look like an " +
                                    "image. Got this as a content type header: <code>%(content_type)s</code>. Please " +
                                    "double check that the URL is returning static images, not multipart data " +
                                    "or videos."
                            );
                            errorText = _.sprintf(errorText, {
                                content_type: _.escape(response.response.content_type)
                            });
                        }

                        showMessageDialog({
                            title: errorTitle,
                            message: errorText,
                            onclose: function () {
                                self.testWebcamSnapshotUrlBusy(false);
                            }
                        });
                        return;
                    }

                    const content = response.response.content;
                    const contentType = response.response.assumed_content_type;

                    const text = gettext(
                        "If you see your webcam snapshot picture below, the entered snapshot URL is ok."
                    );
                    const mimeType = contentType
                        ? contentType.split(";")[0]
                        : "image/jpeg";

                    const textElement = $("<p></p>").text(text);
                    const imgElement = $("<img>")
                        .attr("src", "data:" + mimeType + ";base64," + content)
                        .css("border", "1px solid black");
                    const message = $("<p></p>").append(textElement).append(imgElement);

                    showMessageDialog({
                        title: gettext("Snapshot test"),
                        message: message,
                        onclose: function () {
                            self.testWebcamSnapshotUrlBusy(false);
                        }
                    });
                })
                .fail(function () {
                    showMessageDialog({
                        title: errorTitle,
                        message: errorText,
                        onclose: function () {
                            self.testWebcamSnapshotUrlBusy(false);
                        }
                    });
                });
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ClassicWebcamSettingsViewModel,
        dependencies: ["loginStateViewModel", "settingsViewModel"],
        elements: ["#classicwebcam_settings"]
    });
});
