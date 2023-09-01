$(function () {
    function ClassicWebcamViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settings = parameters[1];
        self.webcamStreamVisible = false;

        self.webcamDisableTimeout = undefined;
        self.webcamLoaded = ko.observable(false);
        self.webcamMjpgEnabled = ko.observable(false);
        self.webcamHlsEnabled = ko.observable(false);
        self.webcamWebRTCEnabled = ko.observable(false);
        self.webcamError = ko.observable(false);
        self.webcamMuted = ko.observable(true);
        self.webRTCPeerConnection = null;
        self.webcamElementHls = null;
        self.webcamElementWebrtc = null;

        self.webcamRatioClass = ko.pureComputed(function () {
            if (self.settings.streamRatio() == "4:3") {
                return "ratio43";
            } else {
                return "ratio169";
            }
        });

        self.webcamClass = ko.pureComputed(function () {
            if (self.settings.rotate90()) {
                return "webcam_rotated " + self.webcamRatioClass();
            } else {
                return "webcam_unrotated " + self.webcamRatioClass();
            }
        });

        self.onBeforeBinding = function () {
            // Subscribe to rotation event to ensure we update calculations.
            // We need to wait for the CSS to be updated by KO, thus we use a timeout to
            // ensure our calculations run after the CSS was updated
            self.settings.rotate90.subscribe(function () {
                window.setTimeout(function () {
                    self._updateVideoTagWebcamLayout();
                }, 1);
            });

            self.streamUrlEscaped = ko.pureComputed(function () {
                return encodeURI(self.settings.streamUrl());
            });

            self.webcamStreamType = ko.pureComputed(function () {
                try {
                    return self.determineWebcamStreamType(self.streamUrlEscaped());
                } catch (e) {
                    console.error(e);
                    self.webcamError(true);
                    return "mjpg";
                }
            });

            self.webcamStreamValid = ko.pureComputed(function () {
                var url = self.streamUrlEscaped();
                return !url || validateWebcamUrl(url);
            });
        };

        self.onWebcamVisibilityChange = function (visible) {
            self.webcamStreamVisible = visible;
            if (self.webcamStreamVisible) {
                self._enableWebcam();
            } else {
                self._disableWebcam();
            }
        };

        self.onWebcamRefresh = function () {
            var streamType = self.webcamStreamType();
            if (streamType == "mjpg") {
                if (OctoPrint.coreui.browser.safari) {
                    // safari bug doesn't release the mjpeg stream, so no reload
                    return;
                }
                $("#webcam_image").attr("src", "");
                self._switchToMjpgWebcam();
                log.info("Triggered refresh of mjpg webcam stream");
            } // no other stream types support refresh yet
        };

        self.onEventSettingsUpdated = function (payload) {
            // the webcam url might have changed, make sure we replace it now if the
            // view is visible
            self._enableWebcamIfVisible();
        };

        self._getActiveWebcamVideoElement = function () {
            if (self.webcamWebRTCEnabled()) {
                return self.webcamElementWebrtc;
            } else {
                return self.webcamElementHls;
            }
        };

        self.launchWebcamPictureInPicture = function () {
            self._getActiveWebcamVideoElement().requestPictureInPicture();
        };

        self.launchWebcamFullscreen = function () {
            self._getActiveWebcamVideoElement().requestFullscreen();
        };

        self.toggleWebcamMute = function () {
            self.webcamMuted(!self.webcamMuted());
            self.webcamElementWebrtc.muted = self.webcamMuted();
            self.webcamElementHls.muted = self.webcamMuted();
        };

        self._disableWebcam = function () {
            // only disable webcam stream if element is out of view for more than 5s,
            // otherwise we might cause more load by the constant connection creation
            // than by the actual webcam stream

            // safari bug doesn't release the mjpeg stream, so we just disable this for
            // safari.
            if (OctoPrint.coreui.browser.safari) {
                return;
            }

            var timeout = self.settings.streamTimeout() || 5;
            self.webcamDisableTimeout = setTimeout(function () {
                log.debug("Unloading webcam stream after", timeout, "seconds");
                $("#webcam_image").attr("src", "");
                self.webcamLoaded(false);
            }, timeout * 1000);
        };

        self._enableWebcamIfVisible = function () {
            if (self.webcamStreamVisible) {
                self._enableWebcam();
            }
        };

        self._enableWebcam = function () {
            if (self.webcamDisableTimeout != undefined) {
                clearTimeout(self.webcamDisableTimeout);
            }

            // If disabled then we dont need to do anything
            if (self.settings.webcamEnabled() == false) {
                console.log("Webcam not enabled");
                return;
            }

            // Determine stream type and switch to corresponding webcam.
            var streamType = self.webcamStreamType();
            if (streamType == "mjpg") {
                self._switchToMjpgWebcam();
            } else if (streamType == "hls") {
                self._switchToHlsWebcam();
            } else if (isWebRTCAvailable() && streamType == "webrtc") {
                self._switchToWebRTCWebcam();
            } else {
                throw "Unknown stream type " + streamType;
            }
        };

        self.onWebcamLoaded = function () {
            if (self.webcamLoaded()) return;

            log.debug("Webcam stream loaded");
            self.webcamLoaded(true);
            self.webcamError(false);
        };

        self.onWebcamErrored = function () {
            log.debug("Webcam stream failed to load/was unloaded");
            self.webcamLoaded(false);
            self.webcamError(true);
        };

        self.onUserPermissionsChanged =
            self.onUserLoggedIn =
            self.onUserLoggedOut =
                function () {
                    self.syncWebcamElements();
                };

        self.syncWebcamElements = function () {
            self.webcamElementHls = document.getElementById("webcam_hls");
            self.webcamElementWebrtc = document.getElementById("webcam_webrtc");
        };

        self.onStartup = function () {
            self.syncWebcamElements();
        };

        self._switchToMjpgWebcam = function () {
            var webcamImage = $("#webcam_image");
            var currentSrc = webcamImage.attr("src");

            // safari bug doesn't release the mjpeg stream, so we just set it up the once
            if (OctoPrint.coreui.browser.safari && currentSrc != undefined) {
                return;
            }

            var newSrc = self.streamUrlEscaped();

            if (currentSrc != newSrc) {
                if (self.settings.cacheBuster()) {
                    if (newSrc.lastIndexOf("?") > -1) {
                        newSrc += "&";
                    } else {
                        newSrc += "?";
                    }
                    newSrc += new Date().getTime();
                }

                self.webcamLoaded(false);
                self.webcamError(false);
                webcamImage.attr("src", newSrc);

                self.webcamHlsEnabled(false);
                self.webcamMjpgEnabled(true);
                self.webcamWebRTCEnabled(false);
            }
        };

        self._switchToHlsWebcam = function () {
            var video = self.webcamElementHls;
            video.onresize = self._updateVideoTagWebcamLayout;

            // Ensure WebRTC is unloaded
            if (self.webRTCPeerConnection != null) {
                self.webRTCPeerConnection.close();
                self.webRTCPeerConnection = null;
            }

            // Check for native playback options: https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/canPlayType
            if (
                video != null &&
                typeof video.canPlayType != undefined &&
                video.canPlayType("application/vnd.apple.mpegurl") == "probably"
            ) {
                video.src = self.streamUrlEscaped();
            } else if (Hls.isSupported()) {
                self.hls = new Hls();
                self.hls.loadSource(self.streamUrlEscaped());
                self.hls.attachMedia(video);
            }

            self.webcamMjpgEnabled(false);
            self.webcamHlsEnabled(true);
            self.webcamWebRTCEnabled(false);
        };

        self._switchToWebRTCWebcam = function () {
            if (!isWebRTCAvailable()) {
                return;
            }
            var video = self.webcamElementWebrtc;
            video.onresize = self._updateVideoTagWebcamLayout;

            // Ensure HLS is unloaded
            if (self.hls != null) {
                self.webcamElementHls.src = null;
                self.hls.destroy();
                self.hls = null;
            }

            // Close any existing, disconnected connection
            if (
                self.webRTCPeerConnection != null &&
                self.webRTCPeerConnection.connectionState != "connected"
            ) {
                self.webRTCPeerConnection.close();
                self.webRTCPeerConnection = null;
            }

            // Open a new connection if necessary
            if (self.webRTCPeerConnection == null) {
                self.webRTCPeerConnection = startWebRTC(
                    video,
                    self.streamUrlEscaped(),
                    self.settings.streamWebrtcIceServers()
                );
            }

            self.webcamMjpgEnabled(false);
            self.webcamHlsEnabled(false);
            self.webcamWebRTCEnabled(true);
        };

        self._updateVideoTagWebcamLayout = function () {
            // Get all elements we need
            var player = self._getActiveWebcamVideoElement();
            var rotationContainer = document.querySelector(
                "#webcam_video_container .webcam_rotated"
            );
            var rotationTarget = document.querySelector(
                "#webcam_video_container .webcam_rotated .rotation_target"
            );
            var unrotationContainer = document.querySelector(
                "#webcam_video_container .webcam_unrotated"
            );
            var unrotationTarget = document.querySelector(
                "#webcam_video_container .webcam_unrotated .rotation_target"
            );

            // If we found the rotation container, the view is rotated 90 degrees. This
            // means we need to manually calculate the player dimensions and apply them
            // to the rotation target where height = width and width = height (to
            // accommodate the rotation). The target is centered in the container and
            // rotated around its center, so after we manually resized the container
            // everything will layout nicely.
            if (rotationContainer) {
                // we'll go with an aspect ration of 1:1 for rotated videos, same as
                // for mjpg streams
                var height = rotationContainer.offsetWidth;

                // Enforce the height on the rotation container and the rotation target.
                // Width of the container will be 100%, height will be calculated
                //
                // The size of the rotation target (the element that has the 90 deg
                // transform) is the inverse size of the container (so height -> width
                // and width -> height)
                rotationContainer.style.height = height + "px";
                rotationTarget.style.height = rotationContainer.offsetWidth + "px";
                rotationTarget.style.width = rotationContainer.offsetHeight + "px";

                // Remove the padding we used to give the element an initial height.
                rotationContainer.style.paddingBottom = 0;
            }

            // We are not rotated, clean up all changes we might have done before
            if (unrotationContainer) {
                unrotationContainer.style.height = null;
                unrotationContainer.style.paddingBottom = 0;
                unrotationTarget.style.height = null;
                unrotationTarget.style.width = null;
            }
        };

        self.determineWebcamStreamType = function (streamUrl) {
            if (!streamUrl) {
                throw "Empty streamUrl. Cannot determine stream type.";
            }

            var parsed = validateWebcamUrl(streamUrl);
            if (!parsed) {
                throw "Invalid streamUrl. Cannot determine stream type.";
            }

            if (parsed.protocol === "webrtc:" || parsed.protocol === "webrtcs:") {
                return "webrtc";
            }

            var lastDotPosition = parsed.pathname.lastIndexOf(".");
            if (lastDotPosition !== -1) {
                var extension = parsed.pathname.substring(lastDotPosition + 1);
                if (extension.toLowerCase() === "m3u8") {
                    return "hls";
                }
            }

            // By default, 'mjpg' is the stream type.
            return "mjpg";
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ClassicWebcamViewModel,
        dependencies: ["loginStateViewModel", "classicWebcamSettingsViewModel"],
        elements: ["#classicwebcam_container"]
    });
});
