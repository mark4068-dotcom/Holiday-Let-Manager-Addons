FROM python:3.15-alpine@sha256:2699b90f4d562a22e2dd076c82f964032f64814204bff36d271a54ba4cc2c7e2

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache openssl

WORKDIR /app
COPY rootfs /
COPY hlm_sheets_service /app/hlm_sheets_service

RUN chmod 755 /run.sh

CMD ["/run.sh"]
