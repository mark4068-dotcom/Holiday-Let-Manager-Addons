FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION=0.4.1
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

COPY component /opt/coastal-water-watch/coastal_water_watch
COPY run.sh /
RUN chmod a+x /run.sh
CMD ["/run.sh"]

