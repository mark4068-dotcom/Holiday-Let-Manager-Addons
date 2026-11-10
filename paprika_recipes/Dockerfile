FROM ghcr.io/home-assistant/base@sha256:8fde4170393bdf7a121ea4d6e34b417e1d0b90125948459f9f9f70cdf5d77c16
ARG BUILD_VERSION=0.3.0
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}"
RUN apk add --no-cache python3
WORKDIR /app
COPY recipe_dashboard /app/recipe_dashboard
COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]
