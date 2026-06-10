ARG DOCKER_ARCH="amd64"
ARG DEBIAN_VERSION="bullseye"
FROM --platform=linux/${DOCKER_ARCH} debian:${DEBIAN_VERSION}-slim AS build_env

RUN apt-get -y update && apt-get -y install curl gnupg2

# Add RPI packages (the whole base system, since RPI ships its own GCC)
ARG DEBIAN_VERSION
ARG BUILD_TYPE="generic"
RUN [ "$BUILD_TYPE" != "raspi" ] || \
  ( \
    ( [ "$(dpkg --print-architecture)" != "armhf" ] || echo "deb http://raspbian.raspberrypi.org/raspbian/ $DEBIAN_VERSION main contrib non-free rpi" > /etc/apt/sources.list.d/raspbian.list ) && \
    echo "deb http://archive.raspberrypi.org/debian/ $DEBIAN_VERSION main" > /etc/apt/sources.list.d/raspi.list && \
    # FIXME: switch key file to pi-gen version once https://github.com/RPi-Distro/pi-gen/pull/863 has been merged
    curl -sL --compressed "https://octoprint.org/files/raspberrypi-keys-sha256.gpg" | gpg --dearmor > /etc/apt/trusted.gpg.d/raspberrypi.gpg \
  )

# Default packages
RUN apt-get -y update \
  && apt-get -y install python3 python3-venv python3-dev git \
     cmake cmake-data g++ libffi-dev libssl-dev \
     libjpeg62-turbo-dev imagemagick

FROM build_env AS build
ADD / /octoprint/src
WORKDIR /octoprint/src
RUN [ "$BUILD_TYPE" != "raspi" ] || \
  echo "[global]\nextra-index-url=https://piwheels.org/simple" > /etc/pip.conf
RUN python3 -m venv /octoprint/venv \
  && /octoprint/venv/bin/pip install .
RUN sha256sum $(find $(/octoprint/venv/bin/pip cache dir) -iname "tornado-*.whl")

FROM build AS runtime
ENTRYPOINT ["/octoprint/venv/bin/octoprint", "serve", "--basedir", "/octoprint/config", "--iknowwhatimdoing"]
