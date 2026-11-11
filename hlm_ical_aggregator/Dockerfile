FROM ghcr.io/home-assistant/base@sha256:58422480a299b16b6ea376c2167463206d430619ed02b40cd687c8bd6875519e

ARG BUILD_VERSION=0.4.3
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache python3 py3-pip \
  && python3 -m venv /opt/hlm \
  && /opt/hlm/bin/pip install --no-cache-dir \
    icalendar==7.3.0 google-auth==2.40.3 requests==2.32.5

WORKDIR /app
COPY src ./src
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["/run.sh"]
