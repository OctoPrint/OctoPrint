ARG DOCKER_ARCH="amd64"
ARG DEBIAN_VERSION="bullseye"
FROM --platform=linux/${DOCKER_ARCH} debian:${DEBIAN_VERSION}-slim AS build_env

RUN apt-get -y update && apt-get -y install gnupg2

# Add RPI packages (the whole base system, since RPI ships its own GCC)
ARG DEBIAN_VERSION
ARG BUILD_TYPE="generic"
RUN [ "$BUILD_TYPE" != "raspi" ] || \
  ( \
    ( [ "$(dpkg --print-architecture)" != "armhf" ] || echo "deb http://raspbian.raspberrypi.org/raspbian/ $DEBIAN_VERSION main contrib non-free rpi" > /etc/apt/sources.list ) && \
    echo "deb http://archive.raspberrypi.org/debian/ $DEBIAN_VERSION main" > /etc/apt/sources.list.d/raspi.list && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 9165938D90FDDD2E 82B129927FA3303E && \
    apt-get -y update \
  )

# Default packages
RUN apt-get -y install python3 python3-venv python3-dev git \
    cmake cmake-data g++ libffi-dev libssl-dev

FROM build_env AS build
ARG OCTO_REF="main"
ADD / /octoprint/src
WORKDIR /octoprint/src
RUN [ "$BUILD_TYPE" != "raspi" ] || \
  echo "[global]\nextra-index-url=https://piwheels.org/simple" > /etc/pip.conf
RUN python3 -m venv /octoprint/venv \
  && ([ "$OCTO_REF" != "main" -o "$DOCKER_ARCH" != "arm/v7" -o "$DEBIAN_VERSION" != "bullseye" ] || /octoprint/venv/bin/pip install markupsafe==3.0.2) \
  && /octoprint/venv/bin/pip install .

FROM build AS runtime
ENTRYPOINT ["/octoprint/venv/bin/octoprint", "serve", "--basedir", "/octoprint/config", "--iknowwhatimdoing"]
